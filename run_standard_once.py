#!/usr/bin/env python3
"""
Ejecuta una sola corrida de análisis estándar (no demo) para diagnóstico.
Uso:
  python run_standard_once.py [hotel] [ciudad]           # pipeline completo
  python run_standard_once.py --report-only <job_id>    # report solo desde briefing_before_report.json
  python run_standard_once.py --render-only <job_id>    # render html solo desde report_normalized.json
Genera data/debug_runs/<job_id>/ con artefactos y summary.json.
"""
import argparse
import asyncio
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

def load_config():
    path = os.path.join(BASE, "config.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

async def main():
    p = argparse.ArgumentParser(description="Run standard analysis or isolated phases")
    p.add_argument("hotel", nargs="?", default="Hotel Arts Barcelona")
    p.add_argument("city", nargs="?", default="Barcelona")
    p.add_argument("--report-only", metavar="JOB_ID", help="Run report agent only from debug_runs/JOB_ID/briefing_before_report.json")
    p.add_argument("--render-only", metavar="JOB_ID", help="Run render only from debug_runs/JOB_ID/report_normalized.json")
    args = p.parse_args()

    hotel = args.hotel
    city = args.city
    cfg = load_config()
    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.render_only:
        print("ERROR: ANTHROPIC_API_KEY o config.json anthropic_api_key requerido")
        sys.exit(1)

    # Modo: report-only desde briefing guardado
    if args.report_only:
        job_id = args.report_only
        debug_dir = os.path.join(BASE, "data", "debug_runs", job_id)
        briefing_path = os.path.join(debug_dir, "briefing_before_report.json")
        if not os.path.isfile(briefing_path):
            print(f"ERROR: {briefing_path} no existe")
            sys.exit(1)
        with open(briefing_path, encoding="utf-8") as f:
            briefing = json.load(f)
        full_analysis = {"hotel_name": briefing.get("hotel_name", "?"), "analysis_date": __import__("datetime").datetime.now().strftime("%Y-%m-%d"), "agent_outputs": {}, "briefing": briefing}
        from agents.agent_07_report import run_report_agent
        report = await run_report_agent(full_analysis, api_key, debug_dir=debug_dir)
        from debug_runs import save_debug_artifact
        save_debug_artifact(debug_dir, "report_normalized", report, as_json=True)
        print("Report-only OK. report_normalized.json guardado.")
        return 0

    # Modo: render-only desde report guardado
    if args.render_only:
        job_id = args.render_only
        debug_dir = os.path.join(BASE, "data", "debug_runs", job_id)
        report_path = os.path.join(debug_dir, "report_normalized.json")
        if not os.path.isfile(report_path):
            print(f"ERROR: {report_path} no existe")
            sys.exit(1)
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        from mailer.report_mailer_v2 import build_email_html_v2
        result = {"report": report, "briefing": {}, "analysis_quality": {}, "evidence_found": {}}
        html = build_email_html_v2(result, report)
        from debug_runs import save_debug_artifact
        save_debug_artifact(debug_dir, "report_html", html, as_json=False)
        print("Render-only OK. report_html.txt guardado.")
        return 0

    import job_state
    import analysis_runner

    job_id = job_state.create_job(BASE, hotel, city, hotel_id=1, fast_demo=False)
    print(f"job_id={job_id} hotel={hotel!r} city={city!r}")
    print("Running standard analysis (no demo)...")

    try:
        await analysis_runner.run_analysis_job(
            base_dir=BASE,
            job_id=job_id,
            hotel_name=hotel,
            city=city,
            api_key=api_key,
            hotel_id=1,
            cfg=cfg,
            send_email=False,
            fast_demo=False,
            get_db_conn=None,
        )
        job = job_state.get_job(BASE, job_id)
        print(f"Done. status={job.get('status')} stage={job.get('stage')}")
        debug_dir = os.path.join(BASE, "data", "debug_runs", job_id)
        if os.path.isdir(debug_dir):
            summary_path = os.path.join(debug_dir, "summary.json")
            if os.path.isfile(summary_path):
                import json
                with open(summary_path, encoding="utf-8") as f:
                    s = json.load(f)
                print("summary.json:", json.dumps(s, indent=2, ensure_ascii=False))
        return 0 if job.get("status") == "completed" else 1
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        debug_dir = os.path.join(BASE, "data", "debug_runs", job_id)
        if os.path.isdir(debug_dir):
            summary_path = os.path.join(debug_dir, "summary.json")
            if os.path.isfile(summary_path):
                import json
                with open(summary_path, encoding="utf-8") as f:
                    s = json.load(f)
                print("summary.json (failure):", json.dumps(s, indent=2, ensure_ascii=False))
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
