"""M1 — Efficiency Audit: MFU/MBU, the GPU-Util lie, and idle waste (deck §5).

Run: python missions/m1_efficiency_audit.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from collections import defaultdict
from missions._common import load_csv, num, catalog_by_type
from finops import metrics


def run(verbose: bool = True) -> dict:
    tel = load_csv("gpu_telemetry.csv")
    cat = catalog_by_type()

    # per-row MFU/MBU, then aggregate per GPU
    agg = defaultdict(lambda: {"util": [], "mfu": [], "mbu": [], "type": None, "idle_hours": 0})
    for r in tel:
        gtype = r["gpu_type"]
        peak_fp16 = num(cat[gtype]["peak_tflops_fp16"])
        peak_bw = num(cat[gtype]["peak_bw_tbs"])
        mfu = metrics.compute_mfu(num(r["achieved_tflops"]), peak_fp16)
        mbu = metrics.compute_mbu(num(r["achieved_bw_tbs"]), peak_bw)
        a = agg[r["gpu_id"]]
        a["type"] = gtype
        a["util"].append(num(r["gpu_util_pct"]))
        a["mfu"].append(mfu)
        a["mbu"].append(mbu)
        if num(r["gpu_util_pct"]) < 10:  # effectively idle this interval (1h)
            a["idle_hours"] += 1

    summary = []
    for gid, a in agg.items():
        summary.append({
            "gpu_id": gid, "gpu_type": a["type"],
            "gpu_util_pct": round(sum(a["util"]) / len(a["util"]), 1),
            "mfu": round(sum(a["mfu"]) / len(a["mfu"]), 3),
            "mbu": round(sum(a["mbu"]) / len(a["mbu"]), 3),
            "idle_hours": a["idle_hours"],
        })

    lies = metrics.flag_util_lies(summary)
    idle_waste = 0.0
    for s in summary:
        on_demand = num(catalog_by_type()[s["gpu_type"]]["on_demand_hr"])
        idle_waste += metrics.idle_waste_usd(s["idle_hours"], on_demand)

    # Extension 2: Right-sizing theo MBU
    cat = catalog_by_type()
    for g in cat.values():
        g["dollars_per_gb"] = num(g["on_demand_hr"]) / num(g["hbm_gb"]) if num(g["hbm_gb"]) > 0 else float('inf')
    
    right_sizing_recs = []
    rs_savings_monthly = 0.0
    for l in lies:
        cur_type = l["gpu_type"]
        cur_cost = num(cat[cur_type]["on_demand_hr"])
        cur_bw = num(cat[cur_type]["peak_bw_tbs"])
        cur_gb = num(cat[cur_type]["hbm_gb"])
        
        # Find cheaper GPU with better or acceptable $/GB-VRAM and lower cost
        best_alt = None
        for g_type, g_data in cat.items():
            if num(g_data["on_demand_hr"]) < cur_cost and g_data["dollars_per_gb"] <= cat[cur_type]["dollars_per_gb"]:
                if not best_alt or g_data["dollars_per_gb"] < cat[best_alt]["dollars_per_gb"]:
                    best_alt = g_type
                    
        if best_alt:
            alt_cost = num(cat[best_alt]["on_demand_hr"])
            savings_pct = (1 - alt_cost / cur_cost) * 100
            monthly_save = (cur_cost - alt_cost) * 24 * 30
            rs_savings_monthly += monthly_save
            right_sizing_recs.append({
                "gpu": l["gpu_id"], "cur_type": cur_type, "cur_cost": cur_cost,
                "cur_bw": cur_bw, "cur_dpgb": cat[cur_type]["dollars_per_gb"],
                "alt_type": best_alt, "alt_cost": alt_cost,
                "alt_bw": num(cat[best_alt]["peak_bw_tbs"]), "alt_dpgb": cat[best_alt]["dollars_per_gb"],
                "savings_pct": savings_pct, "monthly_save": monthly_save
            })

    if verbose:
        print("== M1 Efficiency Audit ==")
        print(f"{'GPU':14}{'type':7}{'util%':>7}{'MFU':>7}{'MBU':>7}{'idle_h':>8}")
        for s in sorted(summary, key=lambda x: x["mfu"]):
            print(f"{s['gpu_id']:14}{s['gpu_type']:7}{s['gpu_util_pct']:>7}{s['mfu']:>7}{s['mbu']:>7}{s['idle_hours']:>8}")
        print(f"\nGPU-Util LIES (util>=90% but MFU<30%): {[l['gpu_id'] for l in lies]}")
        print(f"Idle waste (1 day): ${idle_waste:,.2f}  ->  ${idle_waste*30:,.0f}/month")
        
        print("\n[Extension 2] Right-sizing theo MBU:")
        print(f"{'GPU':14}{'Current':10}{'Proposed':10}{'$/GB (Cur)':>12}{'$/GB (Prop)':>12}{'Savings':>10}")
        for r in right_sizing_recs:
            print(f"{r['gpu']:14}{r['cur_type']:10}{r['alt_type']:10}${r['cur_dpgb']:<11.3f}${r['alt_dpgb']:<11.3f}{r['savings_pct']:.1f}%")
            print(f"  Reason: {r['alt_type']} provides better $/GB-VRAM (${r['alt_dpgb']:.3f} vs ${r['cur_dpgb']:.3f}) and acceptable peak_bw_tbs ({r['alt_bw']} vs {r['cur_bw']}) for memory-bound tasks.")
        print(f"Total potential savings from right-sizing: ${rs_savings_monthly:,.2f}/month")

    return {"summary": summary, "lies": lies, "idle_waste_daily": round(idle_waste, 2), "right_sizing": right_sizing_recs}


if __name__ == "__main__":
    run()
