/**
 * Dead Brands Popup Controller v2 — CMS-managed, config-driven.
 * 
 * Replaces the hardcoded mailing-popup.js with a system that loads
 * popup configs from the CMS and renders them dynamically.
 * 
 * David's spec: popups auto-dismiss after 10 seconds (non-annoying by design).
 * 
 * Behavior:
 * - Loads enabled popups from /content/popups/*.json (via embedded config)
 * - Respects frequency capping (localStorage)
 * - Supports triggers: time_on_page, scroll_depth, exit_intent
 * - Tracks impressions, signups, dismissals
 * - Mailing list signups POST to the real Google Apps Script backend
 */

(function() {
  'use strict';

  // CMS injects popup configs here during build
  var POPUPS = (typeof __POPUP_CONFIGS__ !== 'undefined') ? __POPUP_CONFIGS__ : [];
  
  var MAILING_LIST_ENDPOINT = "https://script.google.com/macros/s/AKfycbwnOSosh68et8uOajfznNiDPSvVFFJjE-EZ0yNvNTr_uPsWjP_jj0ZNJnJfDJzb6gMm/exec";
  var TRACK_ENDPOINT = "/api/cms/popups"; // Portal API for tracking
  
  var LS_PREFIX = "db_popup_";

  // ==========================================================================
  // Frequency Capping
  // ==========================================================================
  
  function getFrequencyState(popupId) {
    try {
      var raw = localStorage.getItem(LS_PREFIX + popupId);
      return raw ? JSON.parse(raw) : { impressions: 0, dismissals: 0, lastShown: 0, subscribed: false };
    } catch (e) {
      return { impressions: 0, dismissals: 0, lastShown: 0, subscribed: false };
    }
  }
  
  function setFrequencyState(popupId, state) {
    try {
      localStorage.setItem(LS_PREFIX + popupId, JSON.stringify(state));
    } catch (e) {}
  }
  
  function shouldShow(popup, state) {
    // Never show if subscribed (for mailing list popups)
    if (popup.type === 'mailing_list' && state.subscribed) return false;
    
    var freq = popup.behavior.frequency || 'once_per_session';
    var now = Date.now();
    
    switch (freq) {
      case 'once_per_session':
        return state.impressions === 0;
      case 'once_per_day':
        return (now - state.lastShown) > (24 * 60 * 60 * 1000);
      case 'until_dismissed_3x':
        return state.dismissals < 3;
      case 'always':
        return true;
      default:
        return state.impressions === 0;
    }
  }
  
  function isScheduled(popup) {
    var now = new Date().toISOString();
    var b = popup.behavior;
    if (b.schedule_start && now < b.schedule_start) return false;
    if (b.schedule_end && now > b.schedule_end) return false;
    return true;
  }
  
  function matchesPage(popup) {
    var targeting = popup.behavior.page_targeting || ['all'];
    if (targeting.includes('all')) return true;
    var path = window.location.pathname;
    return targeting.some(function(pattern) {
      if (pattern === path) return true;
      if (pattern.endsWith('*') && path.startsWith(pattern.slice(0, -1))) return true;
      return false;
    });
  }

  // ==========================================================================
  // Tracking
  // ==========================================================================
  
  function track(popupId, event) {
    // Send to portal API (fire and forget)
    try {
      fetch(TRACK_ENDPOINT + '/' + popupId + '/track', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ event: event })
      }).catch(function() {});
    } catch (e) {}
  }

  // ==========================================================================
  // Rendering
  // ==========================================================================
  
  function createPopupElement(popup) {
    var overlay = document.createElement('div');
    overlay.className = 'db-popup-overlay';
    overlay.id = 'db-popup-' + popup.id;
    overlay.hidden = true;
    
    var theme = popup.design.theme || 'dark';
    var accent = popup.design.accent_color || '#ff6b35';
    var overlayBg = popup.design.background_overlay || 'rgba(0,0,0,0.7)';
    
    overlay.style.cssText = 
      'position:fixed;top:0;left:0;right:0;bottom:0;' +
      'background:' + overlayBg + ';' +
      'display:flex;align-items:center;justify-content:center;' +
      'z-index:9999;opacity:0;transition:opacity 0.3s;';
    
    var cardBg = theme === 'dark' ? '#1a1a1a' : theme === 'light' ? '#ffffff' : '#0f0f0f';
    var textColor = theme === 'light' ? '#333333' : '#e0e0e0';
    
    var card = document.createElement('div');
    card.className = 'db-popup-card';
    card.style.cssText =
      'background:' + cardBg + ';color:' + textColor + ';' +
      'border-radius:12px;padding:32px;max-width:480px;width:90%;' +
      'position:relative;box-shadow:0 20px 60px rgba(0,0,0,0.5);' +
      'transform:translateY(20px);transition:transform 0.3s;';
    
    var html = '<button class="db-popup-close" style="' +
      'position:absolute;top:12px;right:12px;background:none;border:none;' +
      'font-size:24px;cursor:pointer;color:' + textColor + ';opacity:0.6;">×</button>';
    
    html += '<h2 style="margin:0 0 12px 0;font-size:24px;color:' + textColor + ';">' +
            escapeHtml(popup.content.headline) + '</h2>';
    html += '<p style="margin:0 0 20px 0;line-height:1.5;opacity:0.9;">' +
            escapeHtml(popup.content.copy) + '</p>';
    
    if (popup.content.show_email_field) {
      html += '<form class="db-popup-form">';
      if (popup.content.show_name_fields) {
        html += '<input type="text" name="firstName" placeholder="First name" required ' +
                'style="width:100%;padding:12px;margin-bottom:10px;border:1px solid #333;' +
                'border-radius:6px;background:' + (theme === 'light' ? '#f5f5f5' : '#0a0a0a') + ';' +
                'color:' + textColor + ';">';
        html += '<input type="text" name="lastName" placeholder="Last name" required ' +
                'style="width:100%;padding:12px;margin-bottom:10px;border:1px solid #333;' +
                'border-radius:6px;background:' + (theme === 'light' ? '#f5f5f5' : '#0a0a0a') + ';' +
                'color:' + textColor + ';">';
      }
      html += '<input type="email" name="email" placeholder="Email address" required ' +
              'style="width:100%;padding:12px;margin-bottom:12px;border:1px solid #333;' +
              'border-radius:6px;background:' + (theme === 'light' ? '#f5f5f5' : '#0a0a0a') + ';' +
              'color:' + textColor + ';">';
      html += '<button type="submit" style="width:100%;padding:14px;background:' + accent + ';' +
              'color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;">' +
              escapeHtml(popup.content.cta_text) + '</button>';
      html += '<div class="db-popup-status" style="margin-top:10px;font-size:14px;"></div>';
      html += '</form>';
    } else if (popup.content.cta_url) {
      html += '<a href="' + escapeHtml(popup.content.cta_url) + '" ' +
              'style="display:inline-block;padding:14px 28px;background:' + accent + ';' +
              'color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">' +
              escapeHtml(popup.content.cta_text) + '</a>';
    }
    
    card.innerHTML = html;
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    
    return overlay;
  }
  
  function escapeHtml(s) {
    var div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  // ==========================================================================
  // Popup Lifecycle
  // ==========================================================================
  
  function showPopup(popup) {
    var state = getFrequencyState(popup.id);
    if (!shouldShow(popup, state)) return;
    if (!isScheduled(popup)) return;
    if (!matchesPage(popup)) return;
    
    var overlay = document.getElementById('db-popup-' + popup.id);
    if (!overlay) {
      overlay = createPopupElement(popup);
    }
    
    // Track impression
    track(popup.id, 'impression');
    state.impressions++;
    state.lastShown = Date.now();
    setFrequencyState(popup.id, state);
    
    // Show
    overlay.hidden = false;
    requestAnimationFrame(function() {
      overlay.style.opacity = '1';
      overlay.querySelector('.db-popup-card').style.transform = 'translateY(0)';
    });
    document.body.style.overflow = 'hidden';
    
    var interacted = false;
    var autoDismissTimer = null;
    
    function close(dismissed) {
      overlay.style.opacity = '0';
      setTimeout(function() { overlay.hidden = true; }, 300);
      document.body.style.overflow = '';
      if (autoDismissTimer) clearTimeout(autoDismissTimer);
      
      if (dismissed) {
        track(popup.id, 'dismissal');
        var s = getFrequencyState(popup.id);
        s.dismissals++;
        setFrequencyState(popup.id, s);
      }
    }
    
    // Close button
    overlay.querySelector('.db-popup-close').addEventListener('click', function() {
      interacted = true;
      close(true);
    });
    
    // Click outside to dismiss
    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) {
        interacted = true;
        close(true);
      }
    });
    
    // Form submission (mailing list)
    var form = overlay.querySelector('.db-popup-form');
    if (form) {
      form.addEventListener('submit', function(e) {
        e.preventDefault();
        interacted = true;
        
        var formData = new FormData(form);
        var data = {
          firstName: formData.get('firstName') || '',
          lastName: formData.get('lastName') || '',
          email: formData.get('email') || ''
        };
        
        // Validate
        if (!data.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
          showStatus('Please enter a valid email.', 'error');
          return;
        }
        if (popup.content.show_name_fields && (!data.firstName || !data.lastName)) {
          showStatus('Please enter your name.', 'error');
          return;
        }
        
        showStatus('Subscribing...', '');
        
        // POST to real mailing list backend
        fetch(MAILING_LIST_ENDPOINT, {
          method: 'POST',
          mode: 'no-cors', // Apps Script doesn't support CORS preflight
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(data)
        }).then(function() {
          // Success (no-cors means we can't read response, assume OK)
          track(popup.id, 'signup');
          var s = getFrequencyState(popup.id);
          s.subscribed = true;
          setFrequencyState(popup.id, s);
          showStatus('✓ You\'re on the list!', 'success');
          setTimeout(function() { close(false); }, 1500);
        }).catch(function() {
          showStatus('Something went wrong. Try again.', 'error');
        });
        
        function showStatus(msg, kind) {
          var el = overlay.querySelector('.db-popup-status');
          el.textContent = msg;
          el.style.color = kind === 'error' ? '#f85149' : kind === 'success' ? '#3fb950' : 'inherit';
        }
      });
      
      // Any interaction cancels auto-dismiss
      form.addEventListener('input', function() { interacted = true; });
    }
    
    // Auto-dismiss after 10 seconds (David's spec) — unless interacted
    var dismissMs = popup.behavior.auto_dismiss_ms || 10000;
    autoDismissTimer = setTimeout(function() {
      if (!interacted) close(true);
    }, dismissMs);
    
    // Preview mode: don't auto-dismiss
    if (/[?&]preview=popup\b/.test(window.location.search)) {
      if (autoDismissTimer) clearTimeout(autoDismissTimer);
    }
  }

  // ==========================================================================
  // Triggers
  // ==========================================================================
  
  function initTriggers(popup) {
    var triggers = popup.behavior.triggers || ['time_on_page'];
    var delay = popup.behavior.show_delay_ms || 5000;
    
    triggers.forEach(function(trigger) {
      switch (trigger) {
        case 'time_on_page':
          setTimeout(function() { showPopup(popup); }, delay);
          break;
          
        case 'scroll_depth':
          var depth = popup.behavior.scroll_depth_percent || 50;
          var fired = false;
          window.addEventListener('scroll', function() {
            if (fired) return;
            var scrolled = (window.scrollY + window.innerHeight) / document.body.scrollHeight * 100;
            if (scrolled >= depth) {
              fired = true;
              showPopup(popup);
            }
          }, { passive: true });
          break;
          
        case 'exit_intent':
          var exitFired = false;
          document.addEventListener('mouseleave', function(e) {
            if (exitFired) return;
            if (e.clientY <= 0) {
              exitFired = true;
              showPopup(popup);
            }
          });
          break;
      }
    });
  }

  // ==========================================================================
  // Init
  // ==========================================================================
  
  function init() {
    // Only init enabled popups
    POPUPS.filter(function(p) { return p.enabled; }).forEach(function(popup) {
      initTriggers(popup);
    });
  }
  
  // Run when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
})();
var __POPUP_CONFIGS__ = [
  {
    "behavior": {
      "auto_dismiss_ms": 10000,
      "frequency": "once_per_session",
      "page_targeting": [
        "all"
      ],
      "show_delay_ms": 2000,
      "triggers": [
        "time_on_page"
      ]
    },
    "content": {
      "copy": "This is a test popup for verification. It will auto-dismiss in 10 seconds.",
      "cta_text": "Test Subscribe",
      "headline": "TEST: Join the List",
      "show_email_field": true,
      "show_name_fields": true
    },
    "design": {
      "accent_color": "#ff6b35",
      "background_overlay": "rgba(0,0,0,0.75)",
      "button_style": "primary",
      "theme": "dark"
    },
    "enabled": true,
    "id": "test-welcome-001",
    "name": "Test Welcome Popup",
    "stats": {
      "dismissals": 0,
      "impressions": 0,
      "signups": 0
    },
    "type": "mailing_list",
    "updated_ts": "2026-09-30T10:30:00Z"
  }
];
var __POPUP_CONFIGS__ = [
  {
    "behavior": {
      "auto_dismiss_ms": 10000,
      "frequency": "once_per_session",
      "page_targeting": [
        "all"
      ],
      "show_delay_ms": 2000,
      "triggers": [
        "time_on_page"
      ]
    },
    "content": {
      "copy": "This is a test popup for verification. It will auto-dismiss in 10 seconds.",
      "cta_text": "Test Subscribe",
      "headline": "TEST: Join the List",
      "show_email_field": true,
      "show_name_fields": true
    },
    "design": {
      "accent_color": "#ff6b35",
      "background_overlay": "rgba(0,0,0,0.75)",
      "button_style": "primary",
      "theme": "dark"
    },
    "enabled": true,
    "id": "test-welcome-001",
    "name": "Test Welcome Popup",
    "stats": {
      "dismissals": 0,
      "impressions": 0,
      "signups": 0
    },
    "type": "mailing_list",
    "updated_ts": "2026-09-30T10:30:00Z"
  }
];
var __POPUP_CONFIGS__ = [
  {
    "behavior": {
      "auto_dismiss_ms": 10000,
      "frequency": "once_per_session",
      "page_targeting": [
        "all"
      ],
      "show_delay_ms": 2000,
      "triggers": [
        "time_on_page"
      ]
    },
    "content": {
      "copy": "This is a test popup for verification. It will auto-dismiss in 10 seconds.",
      "cta_text": "Test Subscribe",
      "headline": "TEST: Join the List",
      "show_email_field": true,
      "show_name_fields": true
    },
    "design": {
      "accent_color": "#ff6b35",
      "background_overlay": "rgba(0,0,0,0.75)",
      "button_style": "primary",
      "theme": "dark"
    },
    "enabled": true,
    "id": "test-welcome-001",
    "name": "Test Welcome Popup",
    "stats": {
      "dismissals": 0,
      "impressions": 0,
      "signups": 0
    },
    "type": "mailing_list",
    "updated_ts": "2026-09-30T10:30:00Z"
  }
];
var __POPUP_CONFIGS__ = [
  {
    "behavior": {
      "auto_dismiss_ms": 10000,
      "frequency": "once_per_session",
      "page_targeting": [
        "all"
      ],
      "show_delay_ms": 2000,
      "triggers": [
        "time_on_page"
      ]
    },
    "content": {
      "copy": "This is a test popup for verification. It will auto-dismiss in 10 seconds.",
      "cta_text": "Test Subscribe",
      "headline": "TEST: Join the List",
      "show_email_field": true,
      "show_name_fields": true
    },
    "design": {
      "accent_color": "#ff6b35",
      "background_overlay": "rgba(0,0,0,0.75)",
      "button_style": "primary",
      "theme": "dark"
    },
    "enabled": true,
    "id": "test-welcome-001",
    "name": "Test Welcome Popup",
    "stats": {
      "dismissals": 0,
      "impressions": 0,
      "signups": 0
    },
    "type": "mailing_list",
    "updated_ts": "2026-09-30T10:30:00Z"
  }
];
var __POPUP_CONFIGS__ = [
  {
    "behavior": {
      "auto_dismiss_ms": 10000,
      "frequency": "once_per_session",
      "page_targeting": [
        "all"
      ],
      "show_delay_ms": 2000,
      "triggers": [
        "time_on_page"
      ]
    },
    "content": {
      "copy": "This is a test popup for verification. It will auto-dismiss in 10 seconds.",
      "cta_text": "Test Subscribe",
      "headline": "TEST: Join the List",
      "show_email_field": true,
      "show_name_fields": true
    },
    "design": {
      "accent_color": "#ff6b35",
      "background_overlay": "rgba(0,0,0,0.75)",
      "button_style": "primary",
      "theme": "dark"
    },
    "enabled": true,
    "id": "test-welcome-001",
    "name": "Test Welcome Popup",
    "stats": {
      "dismissals": 0,
      "impressions": 0,
      "signups": 0
    },
    "type": "mailing_list",
    "updated_ts": "2026-09-30T10:30:00Z"
  }
];
/* __POPUP_CONFIGS_BAKED__ */
var __POPUP_CONFIGS__ = [
  {
    "behavior": {
      "auto_dismiss_ms": 10000,
      "frequency": "once_per_session",
      "page_targeting": [
        "all"
      ],
      "show_delay_ms": 2000,
      "triggers": [
        "time_on_page"
      ]
    },
    "content": {
      "copy": "This is a test popup for verification. It will auto-dismiss in 10 seconds.",
      "cta_text": "Test Subscribe",
      "headline": "TEST: Join the List",
      "show_email_field": true,
      "show_name_fields": true
    },
    "design": {
      "accent_color": "#ff6b35",
      "background_overlay": "rgba(0,0,0,0.75)",
      "button_style": "primary",
      "theme": "dark"
    },
    "enabled": true,
    "id": "test-welcome-001",
    "name": "Test Welcome Popup",
    "stats": {
      "dismissals": 0,
      "impressions": 0,
      "signups": 0
    },
    "type": "mailing_list",
    "updated_ts": "2026-09-30T10:30:00Z"
  }
];
