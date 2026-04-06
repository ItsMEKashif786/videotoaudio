export default {
  async fetch(request, env, ctx) {
    const BOT_TOKEN = env.BOT_TOKEN || "8733769300:AAGhjsNUxDycsH0YbHZ3I65widx5n-7Dvx8";
    const url = new URL(request.url);
    
    // Route to Telegram API
    const telegramPath = url.pathname;
    const apiUrl = `https://api.telegram.org/bot${BOT_TOKEN}${telegramPath}`;
    
    try {
      const response = await fetch(apiUrl, {
        method: request.method,
        headers: {
          "Content-Type": "application/json",
        },
        body: request.body,
      });
      
      return new Response(response.body, {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    } catch (error) {
      return new Response(JSON.stringify({ ok: false, error: error.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
