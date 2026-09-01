// Client report — ochrana heslom BEZ prihlasovacieho mena (Vercel Edge middleware).
// Vlastný prihlasovací formulár + cookie. Beží aj na free Hobby pláne.
// Heslo a token idú z Vercel Environment Variables (REPORT_PASSWORD, REPORT_TOKEN) - repo je
// public, nesmú byť natvrdo v kóde. Nastav ich vo Vercel dashboarde → Settings → Environment
// Variables, prípadne cez `vercel env add`.
export const config = { matcher: '/((?!favicon.ico|manifest.json|icon-).*)' };

const PASS = process.env.REPORT_PASSWORD;   // heslo na report
const TOKEN = process.env.REPORT_TOKEN;     // hodnota cookie (nie heslo)
const COOKIE = 'report_auth';

function formPage(err) {
  return `<!doctype html><html lang="sk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Valentindance report</title>
<style>
  *{box-sizing:border-box} body{margin:0;height:100vh;display:grid;place-items:center;background:#f4f6f8;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  .box{background:#fff;border:1px solid #e7eaed;border-radius:16px;padding:34px 30px;width:330px;
    box-shadow:0 18px 50px rgba(10,12,14,.12);text-align:center}
  .logo{width:52px;height:52px;border-radius:13px;background:#f72d7f;color:#fff;display:grid;place-items:center;
    font-weight:800;font-size:26px;margin:0 auto 16px;box-shadow:0 6px 16px rgba(247,45,127,.28)}
  h1{font-size:18px;margin:0 0 4px;font-weight:800;color:#0a0c0e}
  p{font-size:13px;color:#7b848c;margin:0 0 18px}
  input{width:100%;font-size:15px;padding:11px 13px;border:1.5px solid #e7eaed;border-radius:10px;font-family:inherit}
  input:focus{outline:none;border-color:#f72d7f}
  button{width:100%;margin-top:11px;font-size:15px;font-weight:800;color:#fff;background:#f72d7f;border:0;
    border-radius:10px;padding:12px;cursor:pointer;font-family:inherit}
  button:hover{background:#c91a63}
  .err{color:#f72d7f;font-size:12.5px;font-weight:700;margin-top:12px}
</style></head><body>
<form method="POST" class="box">
  <div class="logo">V</div>
  <h1>Valentindance report</h1>
  <p>Zadaj heslo pre prístup.</p>
  <input type="password" name="pw" placeholder="Heslo" autofocus autocomplete="current-password" required>
  <button type="submit">Vstúpiť</button>
  ${err ? '<div class="err">Nesprávne heslo.</div>' : ''}
</form></body></html>`;
}

export default async function middleware(request) {
  const cookies = request.headers.get('cookie') || '';
  if (cookies.split(';').some((c) => c.trim() === `${COOKIE}=${TOKEN}`)) return; // už prihlásený

  if (request.method === 'POST') {
    let pw = '';
    try { const f = await request.formData(); pw = f.get('pw') || ''; } catch { /* ignore */ }
    if (pw === PASS) {
      const url = new URL(request.url);
      return new Response(null, {
        status: 303,
        headers: {
          Location: url.pathname,
          'Set-Cookie': `${COOKIE}=${TOKEN}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000`,
        },
      });
    }
    return new Response(formPage(true), { status: 401, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  }

  return new Response(formPage(false), { status: 401, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}
