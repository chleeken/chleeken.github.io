<script>
  (function () {
    // 获取 URL 中的 url 参数，例如 http://a.com/?url=http://b.com
    var params = new URLSearchParams(window.location.search);
    var target = params.get('url');
    if (target) {
      // 简单安全校验：只允许 http/https 开头的地址，防止 javascript: 等恶意跳转
      if (/^https?:\/\//i.test(target)) {
        window.location.replace(target); // 用 replace 不留下历史记录
      }
    }
  })();
</script>