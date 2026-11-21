<#-- Layout delle email di Argo (palette di frontend/DESIGN.md). Non passa da kcSanitize. -->
<#macro emailLayout>
<html lang="${locale.language}" dir="${(ltr)?then('ltr','rtl')}">
<head>
<meta charset="utf-8">
<style>
  body { margin: 0; padding: 0; background: #f6f5f9; }
  .wrap { padding: 32px 16px; font-family: "Hanken Grotesk", "Segoe UI", Arial, sans-serif;
          color: #1d1b26; font-size: 16px; line-height: 1.5; }
  .card { max-width: 520px; margin: 0 auto; background: #fdfcff; border: 1px solid #e3dfec;
          border-top: 4px solid #6e52a3; border-radius: 10px; padding: 28px; }
  .brand { font-weight: 700; font-size: 20px; margin: 0 0 20px; }
  .tile { display: inline-block; width: 26px; height: 26px; line-height: 26px; text-align: center;
          border-radius: 6px; background: #6e52a3; color: #ffffff; font-size: 14px;
          margin-right: 8px; }
  a { color: #6e52a3; }
  .card a.button, .card p a { display: inline-block; background: #6e52a3; color: #ffffff;
          text-decoration: none; font-weight: 600; padding: 12px 20px; border-radius: 6px; }
  .foot { max-width: 520px; margin: 16px auto 0; color: #5f5a70; font-size: 13px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <p class="brand"><span class="tile">A</span>Argo</p>
    <#nested>
  </div>
  <p class="foot">Email automatica di Argo, il sistema che gestisce gli accessi aziendali.</p>
</div>
</body>
</html>
</#macro>
