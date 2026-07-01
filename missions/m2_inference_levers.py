"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0
    
    # Extension 4 trackers
    reasoning_reqs = 0
    total_reqs = len(rows)
    reasoning_cost = 0.0
    reasoning_wh = 0.0
    total_wh = 0.0

    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        is_reasoning = bool(int(num(r.get("is_reasoning", 0))))
        total_tokens += inp + out
        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)
        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        req_cost = pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)
        opt_cost += req_cost
        
        req_wh = sustainability.wh_per_query(inp + out, is_reasoning=is_reasoning)
        total_wh += req_wh
        
        if is_reasoning:
            reasoning_reqs += 1
            reasoning_cost += req_cost
            reasoning_wh += req_wh

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0
    
    reas_traffic_pct = (reasoning_reqs / total_reqs) * 100 if total_reqs > 0 else 0
    reas_cost_pct = (reasoning_cost / opt_cost) * 100 if opt_cost > 0 else 0
    reas_wh_pct = (reasoning_wh / total_wh) * 100 if total_wh > 0 else 0

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")

        print("\n[Extension 4] Ngân sách Reasoning:")
        print(f"Reasoning traffic: {reas_traffic_pct:.1f}% of total queries ({reasoning_reqs}/{total_reqs})")
        print(f"Reasoning cost   : {reas_cost_pct:.1f}% of total optimized cost (${reasoning_cost:.2f}/${opt_cost:.2f})")
        print(f"Reasoning energy : {reas_wh_pct:.1f}% of total energy ({reasoning_wh:.0f} Wh/{total_wh:.0f} Wh)")
        
        print("\nProposed Routing Rule: Cap reasoning queries at 10% of total traffic.")
        if reas_traffic_pct > 10.0:
            allowed_reasoning = int(total_reqs * 0.10)
            capped_reasoning = reasoning_reqs - allowed_reasoning
            # Avg cost and energy per reasoning request
            avg_reas_cost = reasoning_cost / reasoning_reqs
            avg_reas_wh = reasoning_wh / reasoning_reqs
            
            # Avg cost and energy if downgraded to standard (non-reasoning)
            # Roughly, standard energy is 1/80th, and cost might be lower tier. Let's just estimate savings
            # as the difference. But actually if we downgrade, we save. For simplicity, just use avg diff.
            avg_std_cost = (opt_cost - reasoning_cost) / (total_reqs - reasoning_reqs) if (total_reqs - reasoning_reqs) > 0 else 0
            avg_std_wh = (total_wh - reasoning_wh) / (total_reqs - reasoning_reqs) if (total_reqs - reasoning_reqs) > 0 else 0
            
            save_usd = capped_reasoning * (avg_reas_cost - avg_std_cost)
            save_wh = capped_reasoning * (avg_reas_wh - avg_std_wh)
            
            print(f"By downgrading {capped_reasoning} reasoning queries to standard, estimated savings:")
            print(f"  - ${save_usd:.2f} per day")
            print(f"  - {save_wh:,.0f} Wh of energy per day")

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "reasoning_cost": round(reasoning_cost, 2), "reasoning_traffic_pct": round(reas_traffic_pct, 1)
    }


if __name__ == "__main__":
    run()
