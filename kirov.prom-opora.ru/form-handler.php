<?php
/**
 * Обработчик форм заявок лендинга kirov.prom-opora.ru.
 * Пишет заявку в журнал (claims.csv), отправляет письмо, возвращает посетителя
 * на страницу с подтверждением. Без внешних библиотек.
 */
declare(strict_types=1);

/* ===== НАСТРОЙКИ ===== */
const MAIL_TO   = 'АДРЕС_ПОЛУЧАТЕЛЯ';       // получатель заявок
const MAIL_BCC  = 'АДРЕС_СКРЫТОЙ_КОПИИ';                    // скрытая копия
/* Ящик-отправитель: домен 3-го уровня не даёт завести почту на Timeweb,
   поэтому отправляем через SMTP реального ящика домена 2-го уровня */
const SMTP_HOST = 'smtp.timeweb.ru';
const SMTP_PORT = 587;                              // STARTTLS
const SMTP_USER = '[SMTP-пользователь]';
const SMTP_PASS = 'ВСТАВЬТЕ_ПАРОЛЬ';
const MAIL_FROM = '[SMTP-пользователь]';            // совпадает с SMTP_USER
const LOG_FILE  = __DIR__ . '/mail-errors.log';     // причины неудачной отправки
const CSV_FILE  = __DIR__ . '/claims.csv';
const SELF_URL  = 'https://kirov.prom-opora.ru/';

/* Названия форм для журнала и письма */
const FORM_NAMES = [
    'reward'    => 'Оставить заявку',
    'callback'  => 'Заказать звонок',
    'pricelist' => 'Получить прайс-лист',
    'question'  => 'Вопрос / форма контактов',
    'subscribe' => 'Подписка',
];

/* ===== ПОДГОТОВКА ===== */
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: ' . SELF_URL, true, 303);
    exit;
}

function clean(string $v, int $max = 500): string {
    $v = strip_tags(trim($v));
    $v = preg_replace('/\s+/u', ' ', $v) ?? '';
    return mb_substr($v, 0, $max);
}
function fail(string $formId): never {
    header('Location: ' . SELF_URL . '?form=err#' . rawurlencode($formId), true, 303);
    exit;
}

$formId   = clean($_POST['formid'] ?? 'form', 32);
$formName = FORM_NAMES[$formId] ?? 'Форма: ' . $formId;

/* honeypot: скрытое поле должно остаться пустым */
if (clean($_POST['website'] ?? '', 100) !== '') {
    /* притворяемся успешными, чтобы не подсказывать спамерам */
    header('Location: ' . SELF_URL . '?form=ok', true, 303);
    exit;
}

$name    = clean($_POST['name'] ?? '', 120);
$phone   = clean($_POST['phone'] ?? '', 60);
$email   = clean($_POST['email'] ?? '', 120);
$message = clean($_POST['message'] ?? '', 2000);
$consent = isset($_POST['consent']) ? 'да' : 'нет';

/* минимум для работы: имя или телефон */
if ($name === '' && $phone === '' && $email === '') {
    fail($formId);
}
if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    fail($formId);
}

/* ===== ЖУРНАЛ (CSV) ===== */
$header = ['Дата', 'Форма', 'Имя', 'Телефон', 'E-mail', 'Сообщение', 'Согласие', 'IP', 'User-Agent'];
$row = [
    date('Y-m-d H:i:s'), $formName, $name, $phone, $email, $message, $consent,
    $_SERVER['REMOTE_ADDR'] ?? '', mb_substr($_SERVER['HTTP_USER_AGENT'] ?? '', 0, 200),
];
$fp = @fopen(CSV_FILE, 'c+');
if ($fp) {
    if (flock($fp, LOCK_EX)) {
        $stat = fstat($fp);
        if ($stat['size'] === 0) {
            if (function_exists('mb_convert_encoding')) {
                fputcsv($fp, array_map(fn($v) => mb_convert_encoding($v, 'Windows-1251', 'UTF-8'), $header), ';');
            } else {
                fputcsv($fp, $header, ';');
            }
        }
        $enc = function_exists('mb_convert_encoding')
            ? fn($v) => mb_convert_encoding($v, 'Windows-1251', 'UTF-8')
            : fn($v) => $v;
        fputcsv($fp, array_map($enc, $row), ';');
        fflush($fp);
        flock($fp, LOCK_UN);
    }
    fclose($fp);
}

/* ===== ПИСЬМО ===== */
$subject = 'Заявка с kirov.prom-opora.ru: ' . $formName;
$body  = "Новая заявка с лендинга kirov.prom-opora.ru\n\n";
$body .= "Форма:      {$formName}\n";
$body .= "Имя:        {$name}\n";
$body .= "Телефон:    {$phone}\n";
$body .= "E-mail:     {$email}\n";
$body .= "Сообщение:  {$message}\n";
$body .= "Согласие:   {$consent}\n";
$body .= "Дата:       " . date('d.m.Y H:i') . "\n";
$body .= "IP:         " . ($_SERVER['REMOTE_ADDR'] ?? '') . "\n";

/* Протокол SMTP: envelope-адреса задают доставку, поэтому скрытая копия
   добавляется только получателем RCPT TO — заголовок Bcc не пишем */
$rcptTo = [MAIL_TO];
if (MAIL_BCC !== '') {
    $rcptTo[] = MAIL_BCC;
}

/* Отправка по SMTP. Чистый PHP (fsockopen + STARTTLS), без библиотек.
   $smtpLog — стенограмма диалога для журнала ошибок. */
function smtp_send(array $rcptTo, string $messageData, array &$smtpLog): bool {
    $smtpLog = [];
    $fp = @stream_socket_client(
        'tcp://' . SMTP_HOST . ':' . SMTP_PORT, $errno, $errstr, 15
    );
    if (!$fp) {
        $smtpLog[] = 'connect ' . SMTP_HOST . ':' . SMTP_PORT . ' failed: ' . $errstr . ' (' . $errno . ')';
        return false;
    }
    stream_set_timeout($fp, 30);

    $readReply = function () use ($fp): string {
        $reply = '';
        while (($line = fgets($fp, 1024)) !== false) {
            $reply .= $line;
            /* строка ответа заканчивается ' ' после кода, если это последняя */
            if (strlen($line) < 4 || $line[3] === ' ') break;
        }
        return $reply;
    };

    try {
        $step = function (string $code, string $expect) use ($fp, $readReply, &$smtpLog): void {
            fwrite($fp, $code . "\r\n");
            $reply = $readReply();
            /* пароль в стенограмму не пишем */
            $safe = preg_replace('/^(AUTH LOGIN .*)$/i', 'AUTH LOGIN ***', rtrim($code));
            $smtpLog[] = '> ' . $safe . ' / < ' . trim($reply);
            if (strpos($reply, $expect) !== 0) {
                throw new RuntimeException('ожидался ' . $expect . ', получено: ' . trim($reply));
            }
        };

        $readReply();                                   // приветствие сервера
        $step('EHLO kirov.prom-opora.ru', '250');
        $step('STARTTLS', '220');
        if (!stream_socket_enable_crypto($fp, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
            throw new RuntimeException('не удалось начать шифрование после STARTTLS');
        }
        $step('EHLO kirov.prom-opora.ru', '250');
        $step('AUTH LOGIN', '334');
        $step(base64_encode(SMTP_USER), '334');
        $step(base64_encode(SMTP_PASS), '235');
        $step('MAIL FROM:<' . MAIL_FROM . '>', '250');
        foreach ($rcptTo as $rcpt) {
            $step('RCPT TO:<' . $rcpt . '>', '250');
        }
        $step('DATA', '354');
        /* SMTP требует переводы строк CRLF по RFC 5321: сначала все CR убрать,
           затем LF превратить в CRLF, чтобы не задвоить уже готовые CRLF */
        $payload = str_replace(["\r\n", "\n"], ["\n", "\r\n"], $messageData);
        /* экранирование точки в начале строки по RFC 5321 */
        $payload = preg_replace('/^\./m', '..', $payload);
        $written = fwrite($fp, $payload . ".\r\n");
        if ($written === false || $written === 0) {
            throw new RuntimeException('запись письма в сокет не удалась (байт: ' . var_export($written, true) . ')');
        }
        $reply = $readReply();
        $smtpLog[] = '< ' . trim($reply);
        if (strpos($reply, '250') !== 0) {
            throw new RuntimeException('сервер не принял письмо: ' . trim($reply));
        }
        $step('QUIT', '221');
    } catch (Throwable $e) {
        $meta = @stream_get_meta_data($fp);
        $smtpLog[] = 'Ошибка: ' . $e->getMessage()
            . ' (timed_out: ' . ($meta['timed_out'] ? 'да' : 'нет')
            . ', eof: ' . ($meta['eof'] ? 'да' : 'нет') . ')';
        fclose($fp);
        return false;
    }
    fclose($fp);
    return true;
}

function log_mail_error(string $context, array $smtpLog): void {
    $line = '[' . date('Y-m-d H:i:s') . '] ' . $context . "\n";
    if ($smtpLog) {
        $line .= implode("\n", $smtpLog) . "\n";
    }
    @file_put_contents(LOG_FILE, $line, FILE_APPEND | LOCK_EX);
}

/* Тело письма с заголовками (без Bcc — копия идёт через RCPT TO) */
$headers  = 'From: ' . MAIL_FROM . "\r\n";
$headers .= 'Reply-To: ' . ($email !== '' ? $email : MAIL_TO) . "\r\n";
$headers .= 'To: ' . MAIL_TO . "\r\n";
$headers .= 'Subject: =?UTF-8?B?' . base64_encode($subject) . "?=\r\n";
$headers .= 'Date: ' . date('r') . "\r\n";
$headers .= 'Message-ID: <' . md5(uniqid('', true)) . '@kirov.prom-opora.ru>' . "\r\n";
$headers .= 'MIME-Version: 1.0' . "\r\n";
$headers .= 'Content-Type: text/plain; charset=UTF-8' . "\r\n";
$headers .= 'Content-Transfer-Encoding: 8bit';
$messageData = $headers . "\r\n\r\n" . $body;

$smtpLog = [];
$smtpOk = smtp_send($rcptTo, $messageData, $smtpLog);
if (!$smtpOk) {
    /* SMTP не сработал — журнал ошибок и запасной канал mail() */
    log_mail_error('SMTP не удался, переход на mail()', $smtpLog);
    $fallbackHeaders = [
        'From: ' . MAIL_FROM,
        'Reply-To: ' . ($email !== '' ? $email : MAIL_TO),
    ];
    if (MAIL_BCC !== '') {
        $fallbackHeaders[] = 'Bcc: ' . MAIL_BCC;
    }
    $fallbackHeaders[] = 'Content-Type: text/plain; charset=UTF-8';
    $sent = @mail(
        MAIL_TO,
        '=?UTF-8?B?' . base64_encode($subject) . '?=',
        $body,
        implode("\r\n", $fallbackHeaders)
    );
    if (!$sent) {
        log_mail_error('mail() тоже вернул ошибку', []);
    }
}

/* ===== ВОЗВРАТ НА ЛЕНДИНГ ===== */
header('Location: ' . SELF_URL . '?form=ok', true, 303);
exit;