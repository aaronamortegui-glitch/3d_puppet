"""Resolve a filled prompt's inputs to Krea URLs (uploading what is missing) and write a job plan entry.

    python tools/build_plan.py <plan.json> <name> <fill_prompt args...>

Known uploads come from outputs/uploads*.json|txt; new ones go to outputs/uploads_test20.txt.
The presigned upload URL is read from the KREA_PRESIGNED environment variable.
"""
import glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
os.environ["PYTHONIOENCODING"] = "utf-8"


def known():
    k = {}
    for f in sorted(glob.glob("outputs/uploads*.txt")):
        for l in open(f, encoding="utf-8"):
            p = l.split()
            if len(p) >= 2:
                k[p[0].replace("library/", "")] = p[-1]
    for f in glob.glob("outputs/uploads_card_v2.json"):
        for d, u in json.load(open(f)).items():
            k[f"products/{d}/card_v2.png"] = u
    for f in glob.glob("samples/pose_library/jobs_gray_length_variants.tsv"):
        for l in open(f):
            pid, var, job = l.split()
            sku = pid.split("_in_")[0]
            k[f"poses/in_use/{sku}/{pid}/gray_{var}.png"] = f"https://app-uploads.krea.ai/public/{job}-image.png"
    return k


def url(path, k):
    key = path.replace("library/", "")
    if key in k:
        return k[key]
    u = subprocess.run(["curl", "-s", "-F", f"file=@{path}", os.environ["KREA_PRESIGNED"]], capture_output=True, text=True).stdout.strip()
    if not u.startswith("http"):
        raise SystemExit(f"upload failed for {path}: {u}")
    open("outputs/uploads_test20.txt", "a", encoding="utf-8").write(f"{key} {u}\n")
    k[key] = u
    return u


def main():
    plan_f, name, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    o = subprocess.run([sys.executable, "tools/fill_prompt.py"] + args, capture_output=True, text=True, encoding="utf-8").stdout
    head, body = o.split("PROMPT", 1)
    ins = [m for m in re.findall(r"^\s+\d\s+(\S+)", head, re.M) if m.startswith("library/")]
    prompt = body.split("\nNOTE ")[0].strip()
    k = known()
    plan = json.load(open(plan_f)) if os.path.exists(plan_f) else {}
    plan[name] = {"args": args, "inputs": ins, "image_urls": [url(i, k) for i in ins], "prompt": prompt,
                  "notes": re.findall(r"NOTE (.*)", body)}
    json.dump(plan, open(plan_f, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"prompt": prompt, "image_urls": plan[name]["image_urls"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
