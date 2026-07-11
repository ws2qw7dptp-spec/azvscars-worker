const SYSTEM_PROMPT = `You are an expert Azerbaijani automotive journalist writing for a premium Instagram page called @azvscars.
Pick two real, well-known competing cars and write a detailed comparison post in Azerbaijani.

Rules:
- Output ONLY valid JSON, no markdown and no explanation.
- Write natural Azerbaijani with correct spelling.
- Pick controversial, owner-tribe matchups that make people defend their side, similar to Barcelona vs Real Madrid debates.
- Prefer matchups with a clear argument: China vs Germany, EV vs petrol, old-school V8 vs modern hybrid, Toyota/Lexus reliability vs German status, Tesla tech vs BMW/Mercedes luxury, Korean value vs Japanese reliability, American muscle vs European precision.
- The cars do not always need to be exact same-class twins, but they must be realistically cross-shopped or culturally debated by car owners.
- Good examples: BYD Seal vs Mercedes-Benz C-Class, Zeekr 001 vs Mercedes EQE, NIO ET5 vs BMW i4, Li Auto L9 vs Mercedes GLE, Tesla Model 3 Performance vs BMW M3, Toyota Land Cruiser vs Mercedes G-Class, Lexus LX vs Range Rover, old C63 V8 vs new C63 hybrid, Mustang GT vs BMW M4, Hyundai Ioniq 5 N vs Volkswagen Golf R.
- Avoid boring random pairings that will not create comments.
- Avoid recently repeated pairs and avoid repeating the same brand matchup many times in a row.
- Favor cars recognizable in Azerbaijan/Baku car culture, but mix in controversial new Chinese EVs when they can challenge German prestige.
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
    return "POST TYPE: Quick Choice. Pick a highly recognizable tribal matchup that owners will argue about. Strongly prefer China vs Germany, EV vs petrol, Tesla vs German luxury, Japanese reliability vs German prestige, or old V8 vs modern hybrid.";
  }
  if (postType === "war") {
    return "POST TYPE: Comment War. Pick the most controversial status matchup possible: Chinese premium SUV/EV vs Mercedes/BMW/Range Rover, G-Class vs Land Cruiser, Lexus vs Range Rover, Tesla vs BMW/Mercedes, or V8 old generation vs new hybrid. The pair must naturally split car owners into two sides.";
  }
  if (postType === "night") {
    return "POST TYPE: Dark Night Battle. Pick aggressive cars with fanbases: AMG vs M, RS vs M, Mustang vs M4, old V8 AMG vs new hybrid AMG, GT-R vs 911 Turbo, or Hellcat vs European performance.";
  }
  return "POST TYPE: Real VS Battle. Pick a debate-driven matchup with owner loyalty. Prioritize China vs Germany, EV vs petrol, reliability vs prestige, value vs badge, old-school engine vs new technology.";
}

function pairKey(value) {
  const cars = [value.car1_name, value.car2_name]
    .map((name) => String(name || "").toLowerCase().replace(/[^a-z0-9ığüşöçə\s-]/gi, "").trim())
    .sort();
  return cars.join("::");
}

function carKeys(value) {
  return [value.car1_name, value.car2_name]
    .map((name) => String(name || "").toLowerCase().replace(/[^a-z0-9ığüşöçə\s-]/gi, "").trim())
    .filter(Boolean);
}

async function recentPairs(env) {
  if (!env.AZVSCARS_KV) return [];
  const stored = await env.AZVSCARS_KV.get("ai:recent_pairs", "json");
  return Array.isArray(stored) ? stored.slice(0, 30) : [];
}

async function recentCars(env) {
  if (!env.AZVSCARS_KV) return [];
  const stored = await env.AZVSCARS_KV.get("ai:recent_cars", "json");
  return Array.isArray(stored) ? stored.slice(0, 18) : [];
}

async function rememberPair(env, value) {
  if (!env.AZVSCARS_KV) return;
  const key = pairKey(value);
  const recent = await recentPairs(env);
  const next = [key, ...recent.filter((item) => item !== key)].slice(0, 30);
  await env.AZVSCARS_KV.put("ai:recent_pairs", JSON.stringify(next));

  const cars = carKeys(value);
  const storedCars = await recentCars(env);
  const nextCars = [...cars, ...storedCars.filter((item) => !cars.includes(item))].slice(0, 18);
  await env.AZVSCARS_KV.put("ai:recent_cars", JSON.stringify(nextCars));
}

function includesAny(text, items) {
  const lower = String(text || "").toLowerCase();
  return items.some((item) => lower.includes(item));
}

function battleTitleFor(value, postType) {
  const text = `${value.car1_name || ""} ${value.car2_name || ""}`;
  const china = ["byd", "zeekr", "nio", "xpeng", "li auto", "avatr", "hongqi"];
  const german = ["mercedes", "bmw", "audi", "porsche", "volkswagen"];
  const ev = ["tesla", "byd", "zeekr", "nio", "xpeng", "polestar", "ioniq", "taycan", "eqe", "eqs", "bmw i"];
  const suv = ["land cruiser", "g-class", "gle", "glc", "range rover", "lexus lx", "x5", "cayenne", "li auto l9"];
  const muscle = ["mustang", "camaro", "challenger", "hellcat", "corvette"];

  if (includesAny(text, china) && includesAny(text, german)) return "ÇİN VS ALMAN";
  if (includesAny(text, ev) && includesAny(text, german)) return "EV VS BENZİN";
  if (includesAny(text, suv)) return "SUV DÖYÜŞÜ";
  if (includesAny(text, muscle)) return "MUSCLE DÖYÜŞ";
  if (/v8/i.test(`${value.slide2_car1_stat || ""} ${value.slide2_car2_stat || ""}`) && /hybrid|elektrik|erev/i.test(`${value.slide2_car1_stat || ""} ${value.slide2_car2_stat || ""}`)) return "V8 VS HİBRİD";
  if (postType === "night") return "GECƏ DÖYÜŞÜ";
  if (postType === "war") return "ŞƏRH SAVAŞI";
  if (postType === "quick") return "SÜRÜCÜ SEÇİMİ";
  return "AVTO DÖYÜŞÜ";
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
  for (const field of ["slide2_car1_stat", "slide2_car2_stat"]) {
    if (!/HP|Elektrik|EREV/i.test(value[field])) {
      throw new Error(`AI JSON has invalid power stat: ${field}`);
    }
  }
  return value;
}

function normalizeSearchQuery(name) {
  return `${name} side view`;
}

function normalizePowerStat(name, stat) {
  const text = String(stat || "");
  const baseText = text.split(",")[0].trim();
  const hp = text.match(/(\d{3,4})\s*HP/i)?.[1];
  const lowerName = String(name || "").toLowerCase();
  if (lowerName.includes("li auto")) {
    return hp ? `EREV / ${hp} HP` : "EREV";
  }
  const electricNames = [
    "tesla",
    "byd",
    "zeekr",
    "nio",
    "xpeng",
    "avatr",
    "polestar",
    "ioniq",
    "taycan",
    "eqe",
    "eqs",
    "bmw i",
  ];
  const isElectric = electricNames.some((brand) => lowerName.includes(brand));
  if (!isElectric) {
    return baseText || text;
  }
  return hp ? `Elektrik / ${hp} HP` : "Elektrik mühərrik";
}

function polishComparison(value, postType) {
  const clean = { ...value };
  clean.slide2_title = "MÜHƏRRİK VƏ GÜC";
  clean.slide3_title = "0-100 KM/S";
  clean.slide4_title = "BAŞLANĞIC QİYMƏTİ";
  clean.hashtags = "#azvscars #azerbaijan #avto #baku #masin #avtomobil #masinlar";
  clean.car1_search_query = normalizeSearchQuery(clean.car1_name);
  clean.car2_search_query = normalizeSearchQuery(clean.car2_name);
  clean.slide2_car1_stat = normalizePowerStat(clean.car1_name, clean.slide2_car1_stat);
  clean.slide2_car2_stat = normalizePowerStat(clean.car2_name, clean.slide2_car2_stat);
  clean.battle_title = battleTitleFor(clean, postType);

  const a = clean.car1_name || "birinci avtomobil";
  const b = clean.car2_name || "ikinci avtomobil";
  if (postType === "quick") {
    clean.caption = `Sürmək üçün birini seç: ${a} yoxsa ${b}? Bu seçim sadəcə rəqəm deyil, zövq və tərəf məsələsidir. Sənin tərəfin hansıdır? Hər gün yeni avto döyüşlər üçün bizi izlə.`;
  } else if (postType === "war") {
    clean.caption = `Bu duel avtomobil sahiblərini iki yerə böləcək: ${a} yoxsa ${b}? Biri ağılla, biri imiclə qalib gəlir deyənlər olacaq. Sol yoxsa sağ? Cavabı şərhə yaz və bizi izlə.`;
  } else if (postType === "night") {
    clean.caption = `Gecə Bakıda hansının açarını götürərdin: ${a} yoxsa ${b}? Səs, görüntü və xarakter baxımından bu seçim fanatları böləcək. Cavabı şərhə yaz, sabah yeni duel gəlir.`;
  } else {
    clean.caption = `${a} və ${b} eyni səhnədə olsa, mübahisə başlayır. Səncə burada daha vacib olan nədir: marka, texnologiya, etibarlılıq, yoxsa sürüş hissi? Belə müqayisələr üçün bizi izlə.`;
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
  const recent = await recentPairs(env);
  const recentCarList = await recentCars(env);
  const seed = `${Date.now()}-${crypto.randomUUID()}`;
  const prompt = [
    `Generate one fresh car comparison for @azvscars.`,
    `Random seed: ${seed}.`,
    instructionFor(postType),
    `Avoid these recent pair keys: ${recent.slice(0, 12).join(", ") || "none"}.`,
    `Avoid these recent cars completely: ${recentCarList.slice(0, 12).join(", ") || "none"}.`,
    "Avoid repeating common default pairings unless they are uniquely relevant.",
    "Return only the JSON object.",
  ].join("\n");

  try {
    let comparison = null;
    let lastError = null;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const result = await env.AI.run("@cf/meta/llama-3.2-3b-instruct", {
          max_tokens: 1000,
          messages: [
            { role: "system", content: SYSTEM_PROMPT },
            { role: "user", content: `${prompt}\nAttempt: ${attempt + 1}. Pick a different pair if needed.` },
          ],
        });
        const rawComparison = typeof result?.response === "object" ? result.response : extractJson(result?.response);
        const candidate = validateComparison(polishComparison(rawComparison, postType));
        const repeatsPair = recent.includes(pairKey(candidate));
        const repeatsCar = carKeys(candidate).some((car) => recentCarList.includes(car));
        if (!repeatsPair && !repeatsCar) {
          comparison = candidate;
          break;
        }
        lastError = new Error("AI repeated a recent pair or car.");
      } catch (innerError) {
        lastError = innerError;
      }
    }
    if (!comparison) throw lastError || new Error("AI did not produce a fresh comparison.");
    await rememberPair(env, comparison);
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
