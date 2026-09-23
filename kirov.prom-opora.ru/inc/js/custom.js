(function() {
    'use strict';
    
    function replaceSliderLinks() {
        if (typeof UIkit === 'undefined') return;
        
        document.querySelectorAll('.uk-slider-nav').forEach(function(nav) {
            nav.querySelectorAll('a').forEach(function(link) {
                if (link.dataset.replaced === 'true') return;
                
                var button = document.createElement('button');
                button.setAttribute('type', 'button');
                
                var attrs = ['role', 'aria-controls', 'aria-label', 'aria-selected', 'tabindex'];
                attrs.forEach(function(attr) {
                    var value = link.getAttribute(attr);
                    if (value !== null) {
                        button.setAttribute(attr, value);
                    }
                });
                
                button.className = link.className;
                
                button.dataset.replaced = 'true';
                
                link.parentNode.replaceChild(button, link);
            });
        });
    }
    
    function addHrefToFilterCloseButtons() {
        document.querySelectorAll('.wpc-widget-close-icon').forEach(function(link) {
            if (link.dataset.hrefAdded === 'true') return;
            
            link.setAttribute('href', '#');
            
            link.dataset.hrefAdded = 'true';
            
            link.addEventListener('click', function(e) {
                e.preventDefault();
            });
        });
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            if (typeof UIkit !== 'undefined') {
                UIkit.util.ready(replaceSliderLinks);
            }
            addHrefToFilterCloseButtons();
        });
    } else {
        if (typeof UIkit !== 'undefined') {
            UIkit.util.ready(replaceSliderLinks);
        }
        addHrefToFilterCloseButtons();
    }
    
    var observer = new MutationObserver(function(mutations) {
        var shouldReplaceSlider = false;
        var shouldAddHref = false;
        
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // ELEMENT_NODE
                        if (node.classList && 
                            (node.classList.contains('uk-slider-nav') || 
                             node.querySelector('.uk-slider-nav'))) {
                            shouldReplaceSlider = true;
                        }
                        
                        if (node.classList && 
                            (node.classList.contains('wpc-widget-close-icon') || 
                             node.querySelector('.wpc-widget-close-icon'))) {
                            shouldAddHref = true;
                        }
                    }
                });
            }
        });
        
        if (shouldReplaceSlider) {
            setTimeout(replaceSliderLinks, 100);
        }
        
        if (shouldAddHref) {
            setTimeout(addHrefToFilterCloseButtons, 100);
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    setTimeout(replaceSliderLinks, 500);
    setTimeout(replaceSliderLinks, 1000);
    setTimeout(replaceSliderLinks, 2000);
    
    setTimeout(addHrefToFilterCloseButtons, 500);
    setTimeout(addHrefToFilterCloseButtons, 1000);
    setTimeout(addHrefToFilterCloseButtons, 2000);
    
    window.addEventListener('load', function() {
        setTimeout(replaceSliderLinks, 300);
        setTimeout(addHrefToFilterCloseButtons, 300);
    });
})();


document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.antidrone-file-input').forEach(function (input) {
        input.addEventListener('change', function () {
            var namesEl = this.parentElement.querySelector('.antidrone-file-names');
            if (!namesEl) return;
            var files = this.files;
            if (!files || files.length === 0) { namesEl.textContent = ''; return; }
            var names = [];
            for (var i = 0; i < files.length; i++) names.push(files[i].name);
            namesEl.textContent = 'Выбрано файлов: ' + files.length + ' (' + names.join(', ') + ')';
        });
    });
});

document.addEventListener('formit:success', function (e) {
    var form = e.target;
    if (!form || !form.querySelector) return;

    var successEl = form.querySelector('[data-formit-success-message]');
    if (successEl) {
        var msg = '';
        if (e.detail) {
            msg = e.detail.message || e.detail.successMessage || '';
        }
        if (!msg && !successEl.textContent) {
            msg = 'Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.';
        }
        if (msg) successEl.textContent = msg;
        successEl.style.display = 'block';
        successEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    var errorEl = form.querySelector('[data-formit-validation-error-message]');
    if (errorEl) errorEl.style.display = 'none';
});


(function () {
  function loadMap(el) {
    if (el.getAttribute('data-loaded')) return;
    el.setAttribute('data-loaded', '1');
    var s = document.createElement('script');
    s.type = 'text/javascript';
    s.charset = 'utf-8';
    s.async = true;
    s.src = el.getAttribute('data-map-src');
    el.appendChild(s);
    setTimeout(function () {
      var f = el.querySelector('iframe');
      if (f && !f.getAttribute('title')) {
        f.setAttribute('title', 'Яндекс.Карта: адрес и схема проезда');
      }
    }, 2000);
  }
  function init() {
    var maps = document.querySelectorAll('.lazy-map[data-map-src]');
    if (!maps.length) return;
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            loadMap(entry.target);
            io.unobserve(entry.target);
          }
        });
      }, { rootMargin: '150px 0px' });
      maps.forEach(function (m) {
        if (m.closest('.uk-modal')) return;
        io.observe(m);
      });
    } else {
      maps.forEach(function (m) { if (!m.closest('.uk-modal')) loadMap(m); });
    }
    document.addEventListener('show', function (e) {
      var t = e.target;
      if (t && t.classList && t.classList.contains('uk-modal')) {
        t.querySelectorAll('.lazy-map[data-map-src]').forEach(loadMap);
      }
    }, true);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();


// ============================================
// СЛАЙДЕР НА ГЛАВНОЙ: бесконечный цикл, автопрокрутка,
// предзагрузка картинок, точки, стрелки
// ============================================
(function () {
    var root = document.querySelector('.home-slider');
    if (!root) return;
    var frame = root.querySelector('.home-slider-frame');
    var track = frame && frame.querySelector('.home-slider-items');
    if (!frame || !track) return;

    var originals = [].slice.call(track.children);
    var N = originals.length;
    if (!N) return;

    var style2 = root.classList.contains('home-slider--style_2');
    var autoplayAttr = root.getAttribute('data-hs-autoplay');
    var autoplayOn = autoplayAttr === '1' || autoplayAttr === 'true' || autoplayAttr === 'yes';
    var delay = parseInt(root.getAttribute('data-hs-delay'), 10) || 5000;

    originals.forEach(function (li) {
        var url = li.getAttribute('data-bg');
        if (!url) return;
        var bg = li.querySelector('.home-slide-bg');
        if (bg && !bg.style.backgroundImage) bg.style.backgroundImage = 'url(' + url + ')';
        var im = new Image();
        im.src = url;
        if (im.decode) { im.decode().catch(function () {}); }
    });

    var slides, pos, PAD;
    if (N > 1) {
        PAD = 2;
        var head = [], tail = [], i;
        for (i = N - PAD; i < N; i++) head.push(originals[i].cloneNode(true)); // [N-2, N-1]
        for (i = 0; i < PAD; i++) tail.push(originals[i].cloneNode(true));    // [0, 1]

        head.concat(tail).forEach(function (c) {
            c.setAttribute('aria-hidden', 'true');
            [].slice.call(c.querySelectorAll('a')).forEach(function (a) { a.setAttribute('tabindex', '-1'); });
        });
        for (i = head.length - 1; i >= 0; i--) track.insertBefore(head[i], track.firstChild);
        tail.forEach(function (c) { track.appendChild(c); });

        slides = [].slice.call(track.children);
        pos = PAD;
    } else {
        PAD = 0;
        slides = originals;
        pos = 0;
    }

    root.classList.add('is-ready');

    var dotsWrap = root.querySelector('.home-slider-dots');
    if (dotsWrap && N > 1) {
        var d = '';
        for (var k = 0; k < N; k++) {
            d += '<li><button type="button" data-hs-go="' + k + '" aria-label="Слайд ' + (k + 1) + '"></button></li>';
        }
        dotsWrap.innerHTML = d;
    }

    var animating = false, safety = null, timer = null, hover = false;
    var fill = root.querySelector('.home-slider-bg');

    function metrics() {
        var cs = getComputedStyle(track);
        var g = parseFloat(cs.columnGap || cs.gap) || 0;
        return { g: g, w: slides[0].getBoundingClientRect().width, cw: frame.clientWidth };
    }
    function offsetFor(idx) {
        var m = metrics();
        var base = idx * (m.w + m.g);
        return style2 ? -base : (m.cw - m.w) / 2 - base;
    }
    function realIndex() { return N > 1 ? (((pos - PAD) % N) + N) % N : 0; }

    function afterChange() {
        var idx = realIndex();
        if (dotsWrap) {
            var bs = dotsWrap.querySelectorAll('button');
            for (var i = 0; i < bs.length; i++) bs[i].classList.toggle('is-active', i === idx);
        }
        if (fill && originals[idx]) {
            var url = originals[idx].getAttribute('data-bg');
            if (url) fill.style.backgroundImage = 'url(' + url + ')';
        }
    }

    function place(animate) {
        if (animate) {
            animating = true;
            track.style.transition = 'transform .6s ease';
            clearTimeout(safety);
            safety = setTimeout(onEnd, 700);
        } else {
            track.style.transition = 'none';
        }
        track.style.transform = 'translate3d(' + offsetFor(pos) + 'px,0,0)';
        if (!animate) afterChange();
    }

    function onEnd() {
        clearTimeout(safety);
        if (!animating) return;
        animating = false;
        if (N > 1) {
            if (pos >= N + PAD) { pos -= N; place(false); return; }
            if (pos < PAD) { pos += N; place(false); return; }
        }
        afterChange();
    }

    track.addEventListener('transitionend', function (e) {
        if (e.target === track && e.propertyName === 'transform') onEnd();
    });

    function next() { if (animating || N < 2) return; pos += 1; place(true); }
    function prev() { if (animating || N < 2) return; pos -= 1; place(true); }

    function startAuto() {
        stopAuto();
        if (!autoplayOn || N < 2 || hover || document.hidden) return;
        timer = setInterval(next, delay);
    }
    function stopAuto() { if (timer) { clearInterval(timer); timer = null; } }
    root.addEventListener('mouseenter', function () { hover = true; stopAuto(); });
    root.addEventListener('mouseleave', function () { hover = false; startAuto(); });
    document.addEventListener('visibilitychange', startAuto);

    root.addEventListener('click', function (e) {
        var go = e.target.closest('[data-hs-go]');
        if (go) {
            e.preventDefault();
            if (!animating) { pos = PAD + parseInt(go.getAttribute('data-hs-go'), 10); place(true); }
            return;
        }
        if (e.target.closest('.home-slider-prev')) { e.preventDefault(); prev(); return; }
        if (e.target.closest('.home-slider-next')) { e.preventDefault(); next(); }
    });

    var rT;
    window.addEventListener('resize', function () { clearTimeout(rT); rT = setTimeout(function () { place(false); }, 150); });

    place(false);
    startAuto();
})();