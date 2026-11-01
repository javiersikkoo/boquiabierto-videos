"""Montaje de un Short de Boquiabierto (1080x1920, 30 fps).

Uso:  python3 tools/montaje.py config.json

config.json (rutas relativas a "workdir"):
{
  "workdir": "/tmp/short",
  "voice": "voz.mp3",
  "words": "words.json",            # lista de ElevenLabs Scribe: [{"text","start","end"}...]
  "hook": ["TIENE 3 CORAZONES", "(Y UNO SE PARA AL NADAR)"],
  "hook_end": 3.0,
  "keywords": ["TRES", "AZUL.", "DETIENE."],   # palabras que se resaltan en rojo (en mayúsculas, con su puntuación)
  "scenes": [                        # cubren la línea de tiempo de 0 al final sin huecos
    {"clip": "c1.mp4", "start": 0.0, "end": 3.0, "src": 1.6, "reverse": false, "zoom": 1.0, "cx": 0.5, "cy": 0.5},
    {"freeze": "c3.mp4", "at": 5.4, "start": 18.7, "end": 19.6}
  ],
  "beep_at": 18.72,                  # opcional: pitido de monitor (momento de impacto)
  "ambience": "underwater",          # "underwater" | "soft"
  "output": "final.mp4"
}
Si un clip no tiene metraje suficiente desde "src", se ralentiza para cubrir la escena.
"""
import json, os, subprocess, sys

FPS = 30
BAND_Y, BAND_H = 230, 1350


def run(cmd):
    subprocess.run(cmd, check=True)


def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def band_chain(d, zbase, cx, cy, flash, pan=0.0, zmove=0.07):
    z = f"({zbase}+{zmove}*t/{d}+0.20*pow(max(0\\,1-t/0.28)\\,2))"
    cx = f"({cx}+{pan}*t/{d})"
    chain = (
        "[src]split[a][b];"
        "[a]scale=-2:1920,crop=1080:1920,gblur=sigma=38,eq=brightness=-0.22:saturation=1.25[bg];"
        f"[b]scale=w=-2:h='trunc({BAND_H}*{z}/2)*2':eval=frame,"
        f"crop=1080:{BAND_H}:'max(0\\,min(iw-1080\\,iw*{cx}-540))':'max(0\\,min(ih-{BAND_H}\\,ih*{cy}-{BAND_H}/2))'[fg];"
        f"[bg][fg]overlay=0:{BAND_Y}"
    )
    if flash:
        chain += ",fade=t=in:st=0:d=0.12:color=white"
    return chain + ",format=yuv420p[v]"


def main(cfg_path):
    cfg = json.load(open(cfg_path))
    W = cfg["workdir"]
    words_raw = json.load(open(os.path.join(W, cfg["words"])))
    WORDS = [(w["start"], w["end"], w["text"]) for w in words_raw
             if w.get("type", "word") == "word" and not w["text"].startswith("[")]
    END = cfg.get("end") or round(WORDS[-1][1] + 0.35, 2)
    KEY = set(k.upper() for k in cfg.get("keywords", []))
    scenes = cfg["scenes"]
    scenes[-1]["end"] = END
    os.makedirs(f"{W}/sc", exist_ok=True)

    files = []
    for k, s in enumerate(scenes):
        a, b = s["start"], s["end"]
        d = round(b - a, 3)
        n = int(round(b * FPS)) - int(round(a * FPS))
        zb, cx, cy = s.get("zoom", 1.0), s.get("cx", 0.5), s.get("cy", 0.5)
        tmp, out = f"{W}/sc/tmp{k}.mp4", f"{W}/sc/p{k}.mp4"
        if "image" in s:
            # imagen fija con movimiento de cámara (zoom más marcado + paneo lateral)
            pre = f"[0:v]fps={FPS},trim=end_frame={n},setpts=N/{FPS}/TB[src];"
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", f"{W}/{s['image']}"]
            fc = pre + band_chain(d, zb, cx, cy, flash=(k > 0), pan=s.get("pan", 0.08), zmove=s.get("zmove", 0.16))
            run(cmd + ["-filter_complex", fc, "-map", "[v]", "-an", "-frames:v", str(n), "-r", str(FPS),
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", tmp])
            os.rename(tmp, out)
            files.append(out)
            continue
        if "freeze" in s:
            png = f"{W}/sc/freeze{k}.png"
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(s["at"]), "-i", f"{W}/{s['freeze']}", "-frames:v", "1", png])
            pre = (f"[0:v]loop=-1:1,fps={FPS},trim=end_frame={n},setpts=N/{FPS}/TB,"
                   "hue=s=0,colorbalance=rs=0.25:gs=-0.05:bs=-0.05[src];")
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", png]
        else:
            path = f"{W}/{s['clip']}"
            src = s.get("src", 0.0)
            avail = probe_dur(path) - src - 0.05
            if avail >= d:
                flt = f"trim=start={src}:duration={d},setpts=PTS-STARTPTS"
            else:  # ralentizar para cubrir la escena
                flt = f"trim=start={src}:duration={avail:.3f},setpts=(PTS-STARTPTS)*{d / avail:.4f}"
            if s.get("reverse"):
                flt += ",reverse"
            pre = f"[0:v]{flt},fps={FPS},trim=end_frame={n},setpts=N/{FPS}/TB[src];"
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", path]
        fc = pre + band_chain(d, zb, cx, cy, flash=(k > 0))
        run(cmd + ["-filter_complex", fc, "-map", "[v]", "-an", "-frames:v", str(n), "-r", str(FPS),
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", tmp])
        os.rename(tmp, out)
        files.append(out)

    open(f"{W}/sc/list.txt", "w").write("".join(f"file '{p}'\n" for p in files))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{W}/sc/list.txt", "-c", "copy", f"{W}/base.mp4"])

    # ---- subtítulos ----
    def ts(x):
        return f"0:{int(x // 60):02d}:{x % 60:05.2f}"

    groups, cur = [], []
    for w in WORDS:
        cur.append(w)
        if len(cur) == 3 or w[2][-1] in ".,:?!" or len(" ".join(x[2] for x in cur)) > 15:
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    L = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 2", "",
         "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
         "Style: Sub,Inter Display Black,94,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,8,4,5,40,40,0,1",
         "Style: Top,Inter Display Black,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,1,6,3,8,50,50,50,1",
         "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for gi, g in enumerate(groups):
        g_end = groups[gi + 1][0][0] if gi + 1 < len(groups) else END
        g_end = min(g_end, g[-1][1] + 0.6)
        for i, (a, _, _) in enumerate(g):
            end = g[i + 1][0] if i + 1 < len(g) else g_end
            parts = []
            for j, (_, _, ww) in enumerate(g):
                up = ww.upper()
                if j == i:
                    col = "&H3B3BFF&" if up in KEY else "&H00E5FF&"
                    parts.append("{\\c" + col + "\\fscx108\\fscy108}" + up + "{\\c&HFFFFFF&\\fscx100\\fscy100}")
                else:
                    parts.append(up)
            pop = "{\\fscx120\\fscy120\\t(0,100,\\fscx100\\fscy100)}" if i == 0 else ""
            L.append(f"Dialogue: 0,{ts(a)},{ts(end)},Sub,,0,0,0,,{{\\pos(540,1735)}}{pop}" + " ".join(parts))
    hook = cfg.get("hook")
    if hook:
        line = hook[0] + ("\\N{\\c&H00E5FF&}" + hook[1] if len(hook) > 1 else "")
        L.append(f"Dialogue: 1,0:00:00.00,{ts(cfg.get('hook_end', 3.0))},Top,,0,0,0,,{{\\fad(0,200)}}{line}")
    open(f"{W}/subs.ass", "w").write("\n".join(L) + "\n")

    # ---- sonido ----
    amb = ("anoisesrc=d={E}:c=brown:a=0.6,lowpass=f=320,highpass=f=40,volume=0.22"
           if cfg.get("ambience", "underwater") == "underwater"
           else "anoisesrc=d={E}:c=pink:a=0.3,lowpass=f=900,highpass=f=120,volume=0.07").format(E=END)
    inputs = ["-i", f"{W}/base.mp4", "-i", f"{W}/{cfg['voice']}",
              "-f", "lavfi", "-i", amb,
              "-f", "lavfi", "-i", "sine=f=48:d=0.7,afade=t=out:st=0.05:d=0.65,volume=0.9"]
    mix = ["[1:a]volume=1.0[vo]", f"[2:a]afade=t=out:st={END - 0.6}:d=0.6[amb]"]
    labels = ["[vo]", "[amb]", "[3:a]"]
    idx = 4
    for s in scenes[1:]:
        inputs += ["-f", "lavfi", "-i", "anoisesrc=d=0.45:c=pink:a=0.6,bandpass=f=1400:w=1200,afade=t=in:d=0.18,afade=t=out:st=0.18:d=0.27,volume=0.55"]
        ms = max(0, int((s["start"] - 0.2) * 1000))
        mix.append(f"[{idx}:a]adelay={ms}|{ms}[w{idx}]"); labels.append(f"[w{idx}]"); idx += 1
    if cfg.get("beep_at") is not None:
        inputs += ["-f", "lavfi", "-i", "sine=f=1000:d=0.85,afade=t=in:d=0.02,afade=t=out:st=0.7:d=0.15,volume=0.10"]
        ms = int(cfg["beep_at"] * 1000)
        mix.append(f"[{idx}:a]adelay={ms}|{ms}[beep]"); labels.append("[beep]"); idx += 1
    mix.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95[aout]")
    vchain = (f"[0:v]ass={W}/subs.ass[vs];color=c=0xFFE500:s=1080x12:r={FPS}:d={END}[bar];"
              f"[vs][bar]overlay=x='-w+w*t/{END}':y=H-12:shortest=1,format=yuv420p[vout]")
    out = f"{W}/{cfg.get('output', 'final.mp4')}"
    run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(mix) + ";" + vchain,
         "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-c:a", "aac", "-b:a", "192k", "-t", str(END), "-movflags", "+faststart", out + ".tmp.mp4"])
    os.rename(out + ".tmp.mp4", out)
    print(out, END)


if __name__ == "__main__":
    main(sys.argv[1])
