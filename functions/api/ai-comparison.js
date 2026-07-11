const SYSTEM_PROMPT = `You are an expert Azerbaijani automotive journalist writing for a premium Instagram page called @azvscars.
Pick two real, well-known competing cars and write a detailed comparison post in Azerbaijani.

Rules:
- Output ONLY valid JSON, no markdown and no explanation.
- Write natural Azerbaijani with correct spelling.
- Pick direct competitors and vary the pair every time.
- Use accurate real-world specs.
- battle_title must be 2-4 words max.
- Captions must be catchy for car owners and enthusiasts in Azerbaijan.

Required JSON shape:
{
  "car1_name": "BMW M3 Competition",
  "car2_name": "Mercedes-AMG C63 S",
  "car1_search_query": "BMW M3 G80 side view",
  "car2_search_query": "Mercedes AMG C63 W205 side view",
  "battle_title": "ALMAN DÖYÜŞÜ",
  "slide2_title": "MÜHƏRRİK VƏ GÜC",
  "slide2_car1_stat": "3.0L I6 / 503 HP",
  "slide2_car2_stat": "4.0L V8 / 503 HP",
  "slide3_title": "0-100 KM/S",
  "slide3_car1_stat": "3.8 san.",
  "slide3_car2_stat": "3.9 san.",
  "slide4_title": "BAŞLANĞIC QİYMƏTİ",
  "slide4_car1_stat": "$76,000",
  "slide4_car2_stat": "$83,000",
  "caption": "2-4 natural Azerbaijani sentences comparing the cars and asking for comments.",
  "hashtags": "#azvscars #azerbaijan #avto #baku #masin"
}`;

const REQUIRED_FIELDS = [
  "car1_name",
  "car2_name",
  "car1_search_query",
  "car2_search_query",
  "battle_title",
  "slide2_title",
  "slide2_car1_stat",
  "slide2_car2_stat",
  "slide3_title",
  "slide3_car1_stat",
  "slide3_car2_stat",
  "slide4_title",
  "slide4_car1_stat",
  "slide4_car2_stat",
  "caption",
  "hashtags",
];

function instructionFor(postType) {
  if (postType === "quick") {
    return "POST TYPE: Quick Choice. Pick highly recognizable cars. Caption should ask which one they would drive.";
  }
  if (postType === "war") {
    return "POST TYPE: Comment War. Pick expensive status cars around a strong enthusiast budget. Caption must push comments: sol yoxsa sağ?";
  }
  if (postType === "night") {
    return "POST TYPE: Dark Night Battle. Pick aggressive, loud, night-drive cars. Caption should feel bold and short.";
  }
  return "POST TYPE: Real VS Battle. Compare power, speed, price/value, and ask which one wins.";
}

function extractJson(text) {
  const raw = String(text || "").trim();
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1].trim() : raw;
  return JSON.parse(candidate);
}

function validateComparison(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("AI did not return a JSON object.");
  }
  const missing = REQUIRED_FIELDS.filter((field) => typeof value[field] !== "string" || !value[field].trim());
  if (missing.length) {
    throw new Error(`AI JSON missing fields: ${missing.join(", ")}`);
  }
  return value;
}

function polishComparison(value, postType) {
  const clean = { ...value };
  clean.slide2_title = "MÜHƏRRİK VƏ GÜC";
  clean.slide3_title = "0-100 KM/S";
  clean.slide4_title = "BAŞLANĞIC QİYMƏTİ";
  clean.hashtags = "#azvscars #azerbaijan #avto #baku #masin #cars";

  const a = clean.car1_name || "birinci avtomobil";
  const b = clean.car2_name || "ikinci avtomobil";
  if (postType === "quick") {
    clean.battle_title = "SÜRÜCÜ SEÇİMİ";
    clean.caption = `Sürmək üçün birini seç: ${a} yoxsa ${b}? Biri xarakteri ilə, biri performansı ilə diqqət çəkir. Sənin seçimin hansıdır?`;
  } else if (postType === "war") {
    clean.battle_title = "ŞƏRH SAVAŞI";
    clean.caption = `100.000 AZN büdcə olsa hansını alardın: ${a} yoxsa ${b}? Sol yoxsa sağ? Cavabı kommentə yaz.`;
  } else if (postType === "night") {
    clean.battle_title = "GECƏ DÖYÜŞÜ";
    clean.caption = `Gecə Bakıda sürmək üçün hansını seçərdin: ${a} yoxsa ${b}? Səs, görüntü və sürət baxımından bu duel çox sərtdir. Cavabı kommentə yaz.`;
  } else {
    clean.battle_title = "AVTO DÖYÜŞÜ";
    clean.caption = `${a} və ${b} eyni səhnədə olsa, seçim asan deyil. Güc, sürət və qiymət balansında hansını qalib görürsən?`;
  }
  return clean;
}

export async function onRequestPost({ request, env }) {
  if (!env.AI) {
    return new Response(JSON.stringify({ ok: false, error: "Cloudflare AI binding is not configured." }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  let body = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const postType = ["quick", "main", "war", "night"].includes(body.post_type) ? body.post_type : "main";
  const seed = `${Date.now()}-${crypto.randomUUID()}`;
  const prompt = [
    `Generate one fresh car comparison for @azvscars.`,
    `Random seed: ${seed}.`,
    instructionFor(postType),
    "Avoid repeating common default pairings unless they are uniquely relevant.",
    "Return only the JSON object.",
  ].join("\n");

  try {
    const result = await env.AI.run("@cf/meta/llama-3.2-3b-instruct", {
      max_tokens: 1000,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: prompt },
      ],
    });
    const rawComparison = typeof result?.response === "object" ? result.response : extractJson(result?.response);
    const comparison = validateComparison(polishComparison(rawComparison, postType));
    return new Response(JSON.stringify({ ok: true, comparison }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    return new Response(JSON.stringify({ ok: false, error: String(error?.message || error) }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}
