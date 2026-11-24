import os, re, sys, urllib.request, zipfile
REPOS = ["https://dl.google.com/android/maven2/", "https://repo1.maven.org/maven2/"]
OUT = os.path.expanduser("~/ef_billing")
os.makedirs(OUT, exist_ok=True)
seen, log = set(), []

def get(path):
    for r in REPOS:
        try:
            with urllib.request.urlopen(r + path, timeout=30) as f:
                return f.read()
        except Exception:
            pass
    return None

def strip(t):
    return re.sub(r"\{.*?\}", "", t.split("}", 1)[-1]) if t else t

def resolve(g, a, v):
    v = v.strip("[]() ").split(",")[0]
    key = g + ":" + a
    if key in seen or not v:
        return
    seen.add(key)
    base = "%s/%s/%s/%s-%s" % (g.replace(".", "/"), a, v, a, v)
    pom = get(base + ".pom")
    if pom is None:
        log.append("MISSING " + key + ":" + v)
        return
    open(os.path.join(OUT, "%s__%s-%s.pom" % (g, a, v)), "wb").write(pom)
    txt = re.sub(r"<!--.*?-->", "", pom.decode("utf-8", "ignore"), flags=re.S)
    m = re.search(r"<packaging>\s*([^<\s]+)", txt)
    pack = m.group(1) if m else "jar"
    for ext in ([pack] if pack in ("aar", "jar") else []) + ["aar", "jar"]:
        b = get(base + "." + ext)
        if b:
            open(os.path.join(OUT, "%s__%s-%s.%s" % (g, a, v, ext)), "wb").write(b)
            log.append("OK " + key + ":" + v + " " + ext)
            break
    body = txt.split("<dependencyManagement>")[0] + (txt.split("</dependencyManagement>")[1] if "</dependencyManagement>" in txt else "")
    for d in re.findall(r"<dependency>(.*?)</dependency>", body, re.S):
        f = lambda n: (re.search("<%s>\\s*([^<]*?)\\s*</%s>" % (n, n), d) or [None, None])[1]
        if f("scope") in ("test", "provided", "system") or f("optional") == "true":
            continue
        dv = f("version")
        if not dv or "$" in dv or not f("groupId") or not f("artifactId"):
            continue
        resolve(f("groupId"), f("artifactId"), dv)

resolve("com.android.billingclient", "billing", "9.1.0")
seen.add("r8")
r8 = get("com/android/tools/r8/8.7.18/r8-8.7.18.jar")
if r8:
    open(os.path.join(OUT, "r8.jar"), "wb").write(r8); log.append("OK r8")
open(os.path.join(OUT, "log.txt"), "w").write("\n".join(log))
dst = "ef_billing.zip"
if not os.path.isdir(os.path.dirname(dst)):
    dst = os.path.expanduser("~/ef_billing.zip")
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for n in os.listdir(OUT):
        z.write(os.path.join(OUT, n), n)
print("\n".join(log)); print("ZIP:", dst)
