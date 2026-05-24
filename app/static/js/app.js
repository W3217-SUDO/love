// Couple Diary — global client helpers.
// Phase B/C use inline JS in templates for form submission. This file is
// reserved for shared utilities (toast helpers, HTMX defaults, etc.).
(function () {
  'use strict';

  // HTMX global defaults (only applies if HTMX is loaded).
  document.addEventListener('htmx:configRequest', function (evt) {
    // Default to JSON for state-changing requests if Content-Type not set.
    if (evt.detail.verb !== 'get' && !evt.detail.headers['Content-Type']) {
      // Leave default form-encoding; switching to JSON requires per-form opt-in.
    }
  });

  // Suppress unhandled HTMX errors with a visible toast (future).
  document.addEventListener('htmx:responseError', function (evt) {
    console.error('htmx:responseError', evt.detail);
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const message = form.dataset.confirm;
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });

  function base64UrlToUint8Array(value) {
    const padding = '='.repeat((4 - (value.length % 4)) % 4);
    const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = window.atob(base64);
    const output = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) {
      output[i] = raw.charCodeAt(i);
    }
    return output;
  }

  async function enablePushNotifications(statusEl) {
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
      if (statusEl) statusEl.textContent = '当前浏览器不支持推送提醒';
      return;
    }

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      if (statusEl) statusEl.textContent = '未开启通知权限';
      return;
    }

    const keyResponse = await fetch('/notifications/vapid-public-key');
    const keyData = await keyResponse.json();
    if (!keyData.publicKey) {
      if (statusEl) statusEl.textContent = '推送服务尚未配置';
      return;
    }

    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: base64UrlToUint8Array(keyData.publicKey),
    });

    const response = await fetch('/notifications/subscriptions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subscription),
    });

    if (!response.ok) {
      throw new Error('subscription save failed');
    }
    if (statusEl) statusEl.textContent = '推送提醒已开启';
  }

  async function disablePushNotifications(statusEl) {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      if (statusEl) statusEl.textContent = '当前浏览器不支持推送提醒';
      return;
    }

    const registration = await navigator.serviceWorker.getRegistration();
    const subscription = await registration?.pushManager.getSubscription();
    if (!subscription) {
      if (statusEl) statusEl.textContent = '当前没有已开启的推送提醒';
      return;
    }

    const response = await fetch('/notifications/subscriptions/disable', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ endpoint: subscription.endpoint }),
    });

    if (!response.ok) {
      throw new Error('subscription disable failed');
    }

    await subscription.unsubscribe();
    if (statusEl) statusEl.textContent = '推送提醒已关闭';
  }

  function closestButton(event, selector) {
    if (!(event.target instanceof Element)) return null;
    const button = event.target.closest(selector);
    return button instanceof HTMLButtonElement ? button : null;
  }

  document.addEventListener('click', (event) => {
    const button = closestButton(event, '[data-enable-push]');
    if (!button) return;
    const statusEl = document.querySelector('[data-push-status]');
    button.disabled = true;
    if (statusEl) statusEl.textContent = '正在开启推送提醒...';
    enablePushNotifications(statusEl)
      .catch((err) => {
        console.error('push subscription failed', err);
        if (statusEl) statusEl.textContent = '开启失败，请稍后再试';
      })
      .finally(() => {
        button.disabled = false;
      });
  });

  document.addEventListener('click', (event) => {
    const button = closestButton(event, '[data-disable-push]');
    if (!button) return;
    const statusEl = document.querySelector('[data-push-status]');
    button.disabled = true;
    if (statusEl) statusEl.textContent = '正在关闭推送提醒...';
    disablePushNotifications(statusEl)
      .catch((err) => {
        console.error('push disable failed', err);
        if (statusEl) statusEl.textContent = '关闭失败，请稍后再试';
      })
      .finally(() => {
        button.disabled = false;
      });
  });
})();
