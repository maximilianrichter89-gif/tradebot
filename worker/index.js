export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("OK");

    const update = await request.json();
    const message = update.message;
    if (!message?.text) return new Response("OK");

    const chatId = message.chat.id;
    const text = message.text.trim();

    if (!text.startsWith("/trade")) {
      return new Response("OK");
    }

    // Format: /trade [buy|sell] TICKER ANZAHL PREIS
    const parts = text.split(/\s+/);
    let action, ticker, shares, price;

    if (parts.length === 5 && ["buy", "sell"].includes(parts[1].toLowerCase())) {
      [, action, ticker, shares, price] = parts;
      action = action.toLowerCase();
    } else if (parts.length === 4) {
      [, ticker, shares, price] = parts;
      action = "buy";
    } else {
      await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId,
        "Format: /trade [buy|sell] TICKER ANZAHL PREIS\nBeispiel: /trade buy NVDA 8 187.50");
      return new Response("OK");
    }

    ticker = ticker.toUpperCase();
    shares = parseFloat(shares);
    price = parseFloat(price);

    if (isNaN(shares) || isNaN(price) || shares <= 0 || price <= 0) {
      await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId,
        "Ungültige Zahlen.\nBeispiel: /trade buy NVDA 8 187.50");
      return new Response("OK");
    }

    const repo = env.GH_REPO || "maximilianrichter89-gif/tradebot";
    const ghResponse = await fetch(
      `https://api.github.com/repos/${repo}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GH_PAT}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
          "User-Agent": "TradeBot",
        },
        body: JSON.stringify({
          event_type: "trade",
          client_payload: {
            action,
            ticker,
            shares: String(shares),
            price: String(price),
            note: `Telegram @${message.from?.username || message.from?.first_name || "unknown"}`,
          },
        }),
      }
    );

    if (ghResponse.ok) {
      await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId,
        `✅ Trade wird verarbeitet:\n${action.toUpperCase()} ${shares} ${ticker} @ ${price}€\n\nPortfolio aktualisiert sich in ~30 Sekunden.`
      );
    } else {
      await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId,
        "❌ Fehler beim Verarbeiten des Trades. Bitte nochmal versuchen.");
    }

    return new Response("OK");
  },
};

async function sendTelegram(token, chatId, text) {
  return fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text }),
  });
}
