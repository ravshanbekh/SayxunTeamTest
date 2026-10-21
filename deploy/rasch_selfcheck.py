"""
Serverda Rasch hisobini tekshirish (bazaga hech narsa yozmaydi):
    cd /opt/SayxunTeamTest && docker compose exec -T backend python - < deploy/rasch_selfcheck.py
"""
import math, random, os
from types import SimpleNamespace
from app.services.rasch_service import compute_rasch, grade_for, percent_for, subject_points
from app.services.rasch_report_service import RaschReport, RaschRow, item_labels_for, export_rasch_to_pdf

rng = random.Random(2026)
b = [rng.gauss(1.2, 1.2) for _ in range(55)]
X = []
for _ in range(300):
    th = rng.gauss(-0.2, 0.9) if rng.random() < 0.85 else rng.gauss(2.0, 0.8)
    X.append([1 if rng.random() < 1 / (1 + math.exp(-(th - d))) else 0 for d in b])
res = compute_rasch(X)

ok = True
def check(name, cond):
    global ok
    ok = ok and cond
    print(("  OK   " if cond else "  XATO ") + name)

print("Rasch tekshiruvi: 300 talaba x 55 topshiriq (sun'iy, bazaga yozilmaydi)")
check("CML yaqinlashdi", res.converged)
by_raw = {}
for r, s in zip(res.raw_scores, res.scores):
    by_raw.setdefault(r, set()).add(s)
check("bir xil to'g'ri javob -> bir xil ball", all(len(v) == 1 for v in by_raw.values()))
raws = sorted(by_raw)
check("ko'p to'g'ri -> yuqori ball", all(min(by_raw[a]) <= min(by_raw[c]) for a, c in zip(raws, raws[1:])))
check("o'rtacha ball ~50", abs(sum(res.scores) / len(res.scores) - 50) < 0.5)
check("daraja/foiz/fan formulalari", all(
    g == grade_for(s) and p == percent_for(s) and (f1, f2) == subject_points(p)
    for s, g, p, f1, f2 in zip(res.scores, res.grades, res.percents, res.fan1, res.fan2)))
check("rasmdagi qator: 64.73 -> 99.58% B+ 103.61/73.74",
      grade_for(64.73) == "B+" and percent_for(64.73) == 99.58 and subject_points(99.58) == (103.61, 73.74))

counts = {}
for g in res.grades:
    counts[g or "-"] = counts.get(g or "-", 0) + 1
print("  Darajalar:", {k: counts.get(k, 0) for k in ["A+", "A", "B+", "B", "C+", "C", "-"]})
print(f"  Ishonchlilik: {res.reliability:.3f}   Eng yuqori ball: {max(res.scores)}")
order = sorted(range(len(X)), key=lambda i: -res.scores[i])
print("  Top 5 (to'g'ri / ball / daraja):", [(res.raw_scores[i], res.scores[i], res.grades[i]) for i in order[:5]])

rows = [RaschRow(rank=k + 1, result_id=None, user_id=None, name=f"Talaba {i + 1}", region="", correct=res.raw_scores[i],
                 item_values=X[i], theta=res.thetas[i], score=res.scores[i], percent=res.percents[i],
                 grade=res.grades[i], fan1=res.fan1[i], fan2=res.fan2[i]) for k, i in enumerate(order)]
report = RaschReport(test=SimpleNamespace(title="Server tekshiruvi", test_code="SELFCHECK"),
                     test_type="sertifikat", item_labels=item_labels_for("sertifikat"), rows=rows, analysis=res)
path = export_rasch_to_pdf(report, "/tmp/rasch_selfcheck.pdf")
check("PDF yaratildi (shrift bilan)", os.path.getsize(path) > 20000)
print("\nNATIJA:", "HAMMASI TO'G'RI ✅" if ok else "XATO BOR ❌")
