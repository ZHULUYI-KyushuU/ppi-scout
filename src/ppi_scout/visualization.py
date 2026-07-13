"""Build a self-contained, offline HTML view of PPI Scout results."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Iterable, Mapping


MESSAGES: dict[str, dict[str, str]] = {
    "zh-CN": {
        "title": "PPI Scout 本地结果页",
        "model_only": "重要：这里展示的是结构模型证据，不是实验结合证明。",
        "summary": "任务概览",
        "job": "任务",
        "route": "分析路线",
        "status": "运行状态",
        "models": "发现的置信度文件",
        "proteins": "输入蛋白",
        "label": "标签",
        "name": "名称",
        "length": "序列长度",
        "source": "来源",
        "confidence": "原始模型指标",
        "confidence_note": "条形长度只帮助横向比较 0–1 指标；高分不能单独证明发生结合。",
        "metric_help": "常见指标是什么意思",
        "iptm_help": "ipTM / protein_ipTM：模型对链间界面的信心，不是结合概率。",
        "ptm_help": "pTM：模型对整体拓扑关系的信心，不能单独说明界面正确。",
        "plddt_help": "pLDDT / ipLDDT：局部结构或界面原子的模型信心；低值常提示局部不确定。",
        "rank_help": "rank score：同一套设置下给模型排序的综合值；不要把不同流程的数值直接当成亲和力比较。",
        "no_confidence": "没有发现置信度文件：这可能只是计划、dry-run，或者预测尚未完成。",
        "motifs": "AIM/LIR 序列候选",
        "motif_note": "候选分数只是序列启发式排序，不是概率，也不能判断 motif 是否暴露。",
        "candidate": "候选 ID",
        "core": "核心序列",
        "coordinates": "坐标",
        "rank": "排名",
        "score": "序列分数",
        "features": "侧翼特征",
        "selected": "是否已选择",
        "yes": "已选择",
        "no": "未选择",
        "peptides": "短肽与对照面板",
        "peptide_note": "WT 必须和锚点突变、AAAA、scramble 等对照在相同设置下比较。",
        "variant": "变体",
        "kind": "类型",
        "window": "窗口",
        "sequence": "序列",
        "mutation": "改动",
        "kind_wt": "WT（原始序列）",
        "kind_anchor_1_to_a": "第一个锚点突变为 A",
        "kind_anchor_2_to_a": "第二个锚点突变为 A",
        "kind_double_anchor_to_a": "两个锚点都突变为 A",
        "kind_core_to_aaaa": "核心四位全部改为 A",
        "kind_reverse_decoy": "反向核心 decoy",
        "kind_flank_scramble": "保留核心、打乱侧翼",
        "kind_clean_scramble": "组成匹配的完整乱序对照",
        "mutation_flank_scramble": "保留原 motif，分别打乱两侧序列",
        "mutation_clean_scramble": "尽量保持组成一致，并排除 canonical AIM 模式",
        "warnings": "必须注意",
        "how_to_read": "怎么看这个结果",
        "guide_1": "先确认这是真实预测结果，而不是 dry-run。",
        "guide_2": "再比较 WT 与突变、scramble 对照；不要只看 WT 自己高不高。",
        "guide_3": "检查模型是否落在预期结合口袋，并查看 PAE、接触、碰撞和重复模型的一致性。",
        "guide_4": "最后把结论写成“结构模型支持/不支持/仍不确定”，并用实验验证。",
        "raw_warning": "ipTM、pTM、pLDDT、rank score 都是模型指标，不等于亲和力或实验阳性。",
        "warning_scan_pattern": "候选只是 canonical 序列模式匹配，不能证明功能、暴露、无序、磷酸化、互作或结合。",
        "warning_score_heuristic": "序列分数只是启发式优先级，不是概率或模型置信度。",
        "warning_flank_truncated": "要求的侧翼被序列末端截短。",
        "warning_reverse_decoy": "反向核心序列只是压力测试 decoy，不是保证无结合的生物学阴性对照。",
        "warning_accessibility": "短肽预测不能证明该 motif 在全长蛋白中可及。",
        "generated": "该页面由 PPI Scout 在本地生成，不需要联网。",
        "unknown": "未知",
    },
    "en": {
        "title": "PPI Scout local result view",
        "model_only": "Important: this page shows structure-model evidence, not experimental proof of binding.",
        "summary": "Job overview",
        "job": "Job",
        "route": "Analysis route",
        "status": "Run status",
        "models": "Confidence files found",
        "proteins": "Input proteins",
        "label": "Label",
        "name": "Name",
        "length": "Sequence length",
        "source": "Source",
        "confidence": "Raw model metrics",
        "confidence_note": "Bars only aid comparison of 0–1 metrics; a high value alone does not establish binding.",
        "metric_help": "What common metrics mean",
        "iptm_help": "ipTM / protein_ipTM: model confidence in the inter-chain interface, not binding probability.",
        "ptm_help": "pTM: model confidence in overall topology; it cannot establish a correct interface by itself.",
        "plddt_help": "pLDDT / ipLDDT: local model confidence for structure or interface atoms; low values often mark uncertainty.",
        "rank_help": "rank score: a combined model-ranking value under matched settings, not affinity and not directly comparable across workflows.",
        "no_confidence": "No confidence files were found. This may be a plan/dry-run or an incomplete prediction.",
        "motifs": "AIM/LIR sequence candidates",
        "motif_note": "Candidate scores are sequence heuristics, not probabilities, and cannot establish motif accessibility.",
        "candidate": "Candidate ID",
        "core": "Core",
        "coordinates": "Coordinates",
        "rank": "Rank",
        "score": "Sequence score",
        "features": "Flank features",
        "selected": "Selected",
        "yes": "yes",
        "no": "no",
        "peptides": "Peptide and control panels",
        "peptide_note": "Compare WT with anchor mutants, AAAA, and scrambles under identical settings.",
        "variant": "Variant",
        "kind": "Kind",
        "window": "Window",
        "sequence": "Sequence",
        "mutation": "Change",
        "kind_wt": "WT (original sequence)",
        "kind_anchor_1_to_a": "first anchor to A",
        "kind_anchor_2_to_a": "second anchor to A",
        "kind_double_anchor_to_a": "both anchors to A",
        "kind_core_to_aaaa": "four-residue core to AAAA",
        "kind_reverse_decoy": "reverse-core decoy",
        "kind_flank_scramble": "core retained, flanks scrambled",
        "kind_clean_scramble": "composition-matched full scramble",
        "mutation_flank_scramble": "native motif retained; flanks independently shuffled",
        "mutation_clean_scramble": "composition matched; canonical AIM pattern excluded",
        "warnings": "Important cautions",
        "how_to_read": "How to read this result",
        "guide_1": "Confirm that this is a completed prediction rather than a dry-run.",
        "guide_2": "Compare WT against mutants and scrambles; do not judge WT in isolation.",
        "guide_3": "Check the expected pocket, PAE, contacts, clashes, and pose consistency across models.",
        "guide_4": "Conclude model support, lack of support, or uncertainty, then validate experimentally.",
        "raw_warning": "ipTM, pTM, pLDDT, and rank score are model metrics, not affinity or experimental positivity.",
        "warning_scan_pattern": "Candidates are canonical sequence-pattern matches only; they do not establish function, exposure, disorder, phosphorylation, interaction, or binding.",
        "warning_score_heuristic": "Sequence scores are heuristic priorities, not probabilities or model confidence.",
        "warning_flank_truncated": "The requested flank was truncated by a sequence terminus.",
        "warning_reverse_decoy": "A reverse-core variant is a stress-test decoy, not a guaranteed biological negative.",
        "warning_accessibility": "Peptide predictions do not establish motif accessibility in the full-length protein.",
        "generated": "Generated locally by PPI Scout; no network connection is required.",
        "unknown": "unknown",
    },
    "ja": {
        "title": "PPI Scout ローカル結果ページ",
        "model_only": "重要：ここに示すのは構造モデルの根拠であり、実験的な結合証明ではありません。",
        "summary": "ジョブ概要",
        "job": "ジョブ",
        "route": "解析ルート",
        "status": "実行状態",
        "models": "検出された信頼度ファイル",
        "proteins": "入力タンパク質",
        "label": "ラベル",
        "name": "名称",
        "length": "配列長",
        "source": "ソース",
        "confidence": "生のモデル指標",
        "confidence_note": "バーは0–1指標の比較補助にすぎず、高値だけで結合は証明できません。",
        "metric_help": "主な指標の意味",
        "iptm_help": "ipTM / protein_ipTM：鎖間界面に対するモデル信頼度であり、結合確率ではありません。",
        "ptm_help": "pTM：全体トポロジーに対するモデル信頼度で、界面の正しさを単独では示しません。",
        "plddt_help": "pLDDT / ipLDDT：局所構造または界面原子のモデル信頼度で、低値は不確実性を示すことがあります。",
        "rank_help": "rank score：同一条件内の総合ランキング値で、親和性ではなく異なる手順間で直接比較できません。",
        "no_confidence": "信頼度ファイルが見つかりません。計画、dry-run、または未完了の予測かもしれません。",
        "motifs": "AIM/LIR 配列候補",
        "motif_note": "候補スコアは配列ヒューリスティックであり、確率でも露出の証明でもありません。",
        "candidate": "候補ID",
        "core": "コア配列",
        "coordinates": "座標",
        "rank": "順位",
        "score": "配列スコア",
        "features": "フランク特徴",
        "selected": "選択済み",
        "yes": "はい",
        "no": "いいえ",
        "peptides": "ペプチドと対照パネル",
        "peptide_note": "WTとアンカー変異、AAAA、scrambleを同一条件で比較してください。",
        "variant": "変異体",
        "kind": "種類",
        "window": "ウィンドウ",
        "sequence": "配列",
        "mutation": "変更",
        "kind_wt": "WT（元配列）",
        "kind_anchor_1_to_a": "第1アンカーをAへ置換",
        "kind_anchor_2_to_a": "第2アンカーをAへ置換",
        "kind_double_anchor_to_a": "両アンカーをAへ置換",
        "kind_core_to_aaaa": "4残基コアをAAAAへ置換",
        "kind_reverse_decoy": "逆向きコアdecoy",
        "kind_flank_scramble": "コア保持・フランクシャッフル",
        "kind_clean_scramble": "組成を合わせた全配列シャッフル対照",
        "mutation_flank_scramble": "元のmotifを保持し、両側フランクを別々にシャッフル",
        "mutation_clean_scramble": "組成をできるだけ維持し、canonical AIMパターンを除外",
        "warnings": "重要な注意",
        "how_to_read": "結果の読み方",
        "guide_1": "dry-runではなく、完了した予測であることを確認します。",
        "guide_2": "WT単独ではなく、変異体とscramble対照を比較します。",
        "guide_3": "予想ポケット、PAE、接触、衝突、モデル間のポーズ一致を確認します。",
        "guide_4": "モデル支持・不支持・不確実のいずれかとして結論し、実験で検証します。",
        "raw_warning": "ipTM、pTM、pLDDT、rank scoreはモデル指標であり、親和性や実験陽性ではありません。",
        "warning_scan_pattern": "候補はcanonical配列パターンとの一致にすぎず、機能、露出、天然変性、リン酸化、相互作用、結合を証明しません。",
        "warning_score_heuristic": "配列スコアはヒューリスティックな優先順位であり、確率やモデル信頼度ではありません。",
        "warning_flank_truncated": "要求したフランクが配列末端で短縮されています。",
        "warning_reverse_decoy": "逆向きコアはストレステスト用decoyであり、保証された生物学的陰性対照ではありません。",
        "warning_accessibility": "ペプチド予測は全長タンパク質中のモチーフ露出を証明しません。",
        "generated": "PPI Scoutがローカルで生成したページで、ネット接続は不要です。",
        "unknown": "不明",
    },
}


def _messages(language: str | None) -> Mapping[str, str]:
    if language and language.lower().startswith("zh"):
        return MESSAGES["zh-CN"]
    if language and language.lower().startswith("ja"):
        return MESSAGES["ja"]
    return MESSAGES["en"]


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return escape(fallback)
    return escape(str(value))


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_cell(value: Any) -> str:
    number = _number(value)
    label = _text(value)
    if number is None or number < 0 or number > 1:
        return f"<span class=\"metric-value\">{label}</span>"
    width = max(0.0, min(100.0, number * 100.0))
    return (
        f"<span class=\"metric-value\">{label}</span>"
        f"<span class=\"meter\" role=\"img\" aria-label=\"{label}\">"
        f"<span style=\"width:{width:.1f}%\"></span></span>"
    )


def _protein_table(job: Mapping[str, Any], m: Mapping[str, str]) -> str:
    inputs = job.get("inputs", {})
    proteins = inputs.get("proteins", []) if isinstance(inputs, Mapping) else []
    if not isinstance(proteins, list) or not proteins:
        return ""
    rows: list[str] = []
    for index, protein in enumerate(proteins):
        if not isinstance(protein, Mapping):
            continue
        sequence = protein.get("sequence")
        length = len(sequence) if isinstance(sequence, str) else m["unknown"]
        rows.append(
            "<tr>"
            f"<td><span class=\"tag\">{_text(protein.get('id') or chr(65 + index))}</span></td>"
            f"<td>{_text(protein.get('name'), m['unknown'])}</td>"
            f"<td>{_text(length)}</td>"
            f"<td>{_text(protein.get('source'), m['unknown'])}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return (
        f"<section><h2>{m['proteins']}</h2><div class=\"table-wrap\"><table>"
        f"<thead><tr><th>{m['label']}</th><th>{m['name']}</th><th>{m['length']}</th>"
        f"<th>{m['source']}</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>"
    )


def _confidence_table(rows: Iterable[Mapping[str, Any]], m: Mapping[str, str]) -> str:
    materialized = [dict(row) for row in rows]
    if not materialized:
        return (
            f"<section><h2>{m['confidence']}</h2><p class=\"empty\">{m['no_confidence']}</p>"
            f"{_metric_help(m)}</section>"
        )
    keys = sorted({key for row in materialized for key in row if key != "source"})
    header = "".join(f"<th>{_text(key)}</th>" for key in keys)
    body: list[str] = []
    for row in materialized:
        values = "".join(f"<td>{_metric_cell(row.get(key, ''))}</td>" for key in keys)
        body.append(f"<tr><td><code>{_text(row.get('source', ''))}</code></td>{values}</tr>")
    return (
        f"<section><h2>{m['confidence']}</h2><p class=\"note\">{m['confidence_note']}</p>"
        f"<div class=\"table-wrap\"><table><thead><tr><th>{m['source']}</th>{header}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
        f"{_metric_help(m)}</section>"
    )


def _metric_help(m: Mapping[str, str]) -> str:
    return (
        f"<details><summary>{m['metric_help']}</summary><ul>"
        f"<li>{m['iptm_help']}</li><li>{m['ptm_help']}</li>"
        f"<li>{m['plddt_help']}</li><li>{m['rank_help']}</li>"
        "</ul></details>"
    )


def _motif_table(scan: Mapping[str, Any], m: Mapping[str, str]) -> str:
    candidates = scan.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        return ""
    selected = {str(value) for value in scan.get("designed_candidate_ids", [])}
    scores = [_number(item.get("sequence_score")) for item in candidates if isinstance(item, Mapping)]
    maximum = max((value for value in scores if value is not None), default=0.0)
    rows: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        candidate_id = str(candidate.get("candidate_id", ""))
        score = _number(candidate.get("sequence_score"))
        score_bar = ""
        if score is not None and maximum > 0:
            width = max(0.0, min(100.0, score / maximum * 100.0))
            score_bar = f"<span class=\"meter heuristic\"><span style=\"width:{width:.1f}%\"></span></span>"
        coordinates = f"{candidate.get('start_1based', '?')}–{candidate.get('end_1based', '?')}"
        features = (
            f"D/E={candidate.get('acidic_flank_count', '?')}; "
            f"S/T={candidate.get('serine_threonine_flank_count', '?')}"
        )
        rows.append(
            "<tr>"
            f"<td><code>{_text(candidate_id)}</code></td>"
            f"<td><code>{_text(candidate.get('core_sequence', ''))}</code></td>"
            f"<td>{_text(coordinates)}</td><td>{_text(candidate.get('rank', ''))}</td>"
            f"<td>{_text(candidate.get('sequence_score', ''))}{score_bar}</td>"
            f"<td>{_text(features)}</td>"
            f"<td>{m['yes'] if candidate_id in selected else m['no']}</td>"
            "</tr>"
        )
    return (
        f"<section><h2>{m['motifs']}</h2><p class=\"note\">{m['motif_note']}</p>"
        f"<div class=\"table-wrap\"><table><thead><tr><th>{m['candidate']}</th><th>{m['core']}</th>"
        f"<th>{m['coordinates']}</th><th>{m['rank']}</th><th>{m['score']}</th>"
        f"<th>{m['features']}</th><th>{m['selected']}</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
    )


def _peptide_tables(scan: Mapping[str, Any], m: Mapping[str, str]) -> str:
    panels = scan.get("peptide_panels", [])
    if not isinstance(panels, list) or not panels:
        return ""
    details: list[str] = []
    for panel_entry in panels:
        if not isinstance(panel_entry, Mapping):
            continue
        candidate_id = panel_entry.get("candidate_id", "")
        design = panel_entry.get("design", {})
        panel = design.get("panel", {}) if isinstance(design, Mapping) else {}
        variants = panel.get("variants", []) if isinstance(panel, Mapping) else []
        rows: list[str] = []
        for variant in variants if isinstance(variants, list) else []:
            if not isinstance(variant, Mapping):
                continue
            raw_kind = str(variant.get("kind", ""))
            kind = m.get(f"kind_{raw_kind}", raw_kind)
            raw_mutation = variant.get("mutation") or "—"
            if raw_mutation == "native motif retained; flanks independently shuffled":
                mutation = m["mutation_flank_scramble"]
            elif raw_mutation == "composition-matched; canonical AIM pattern excluded":
                mutation = m["mutation_clean_scramble"]
            else:
                mutation = str(raw_mutation)
            rows.append(
                "<tr>"
                f"<td><code>{_text(variant.get('variant_id', ''))}</code></td>"
                f"<td>{_text(kind)}</td>"
                f"<td>{_text(variant.get('actual_window', ''))}</td>"
                f"<td><code class=\"sequence\">{_text(variant.get('sequence', ''))}</code></td>"
                f"<td>{_text(mutation)}</td>"
                "</tr>"
            )
        details.append(
            f"<details><summary>{m['candidate']}: <code>{_text(candidate_id)}</code> · "
            f"{len(rows)} {m['variant']}</summary><div class=\"table-wrap\"><table>"
            f"<thead><tr><th>{m['variant']}</th><th>{m['kind']}</th><th>{m['window']}</th>"
            f"<th>{m['sequence']}</th><th>{m['mutation']}</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div></details>"
        )
    if not details:
        return ""
    return (
        f"<section><h2>{m['peptides']}</h2><p class=\"note\">{m['peptide_note']}</p>"
        f"{''.join(details)}</section>"
    )


def _warning_section(
    job: Mapping[str, Any],
    scan: Mapping[str, Any],
    status: Mapping[str, Any],
    m: Mapping[str, str],
) -> str:
    warnings: list[str] = []

    def add_many(values: Any, prefix: str = "") -> None:
        if not isinstance(values, (list, tuple)):
            return
        for value in values:
            rendered = f"{prefix}{value}"
            if rendered not in warnings:
                warnings.append(rendered)

    routing = job.get("routing", {})
    if isinstance(routing, Mapping):
        add_many(routing.get("warnings"))
    add_many(scan.get("warnings"))
    candidates = scan.get("candidates", [])
    for candidate in candidates if isinstance(candidates, list) else []:
        if isinstance(candidate, Mapping):
            add_many(candidate.get("warnings"), f"{candidate.get('candidate_id', 'candidate')}: ")
    panels = scan.get("peptide_panels", [])
    for panel_entry in panels if isinstance(panels, list) else []:
        if not isinstance(panel_entry, Mapping):
            continue
        design = panel_entry.get("design", {})
        panel = design.get("panel", {}) if isinstance(design, Mapping) else {}
        if isinstance(panel, Mapping):
            add_many(panel.get("warnings"), f"{panel_entry.get('candidate_id', 'panel')}: ")
    if status.get("error"):
        warnings.insert(0, f"status: {status['error']}")
    if not warnings:
        return ""
    translations = (
        ("Candidates are canonical sequence-pattern matches only", "warning_scan_pattern"),
        ("Sequence scores are heuristic", "warning_score_heuristic"),
        ("The requested flank was truncated", "warning_flank_truncated"),
        ("Reverse-core variants are decoys", "warning_reverse_decoy"),
        ("Peptide predictions do not establish motif accessibility", "warning_accessibility"),
    )

    def localize(value: str) -> str:
        for phrase, key in translations:
            if phrase in value:
                prefix = value[: value.index(phrase)]
                return prefix + m[key]
        return value

    items = "".join(f"<li>{_text(localize(warning))}</li>" for warning in warnings)
    return f"<section><h2>{m['warnings']}</h2><ul>{items}</ul></section>"


def build_html_report(
    job: Mapping[str, Any] | None,
    rows: Iterable[Mapping[str, Any]],
    *,
    scan: Mapping[str, Any] | None = None,
    status: Mapping[str, Any] | None = None,
    language: str | None = None,
) -> str:
    """Return a complete standalone HTML document with no network dependencies."""

    job = dict(job or {})
    status = dict(status or {})
    scan = dict(scan or (job.get("motif_scan") if isinstance(job.get("motif_scan"), Mapping) else {}))
    language = language or str(job.get("language") or "en")
    m = _messages(language)
    materialized_rows = [dict(row) for row in rows]
    routing = job.get("routing", {})
    execution = job.get("execution", {})
    route = (
        routing.get("route", job.get("resolved_workflow", m["unknown"]))
        if isinstance(routing, Mapping)
        else job.get("resolved_workflow", m["unknown"])
    )
    run_status = status.get("status")
    if run_status is None:
        run_status = execution.get("status", m["unknown"]) if isinstance(execution, Mapping) else m["unknown"]
    name = job.get("name", scan.get("kind", "PPI Scout"))
    warning_items = "".join(
        f"<li>{m[key]}</li>" for key in ("guide_1", "guide_2", "guide_3", "guide_4")
    )
    return f"""<!doctype html>
<html lang="{_text(language)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{m['title']} · {_text(name)}</title>
<style>
:root {{ color-scheme: light dark; --bg:#f6f7f9; --panel:#ffffff; --text:#172033; --muted:#5f6b7a; --border:#dce1e8; --accent:#3157d5; --accent-soft:#e9eeff; --warn:#8a5400; --warn-bg:#fff5d9; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#10131a; --panel:#191e28; --text:#eef2f8; --muted:#aab4c2; --border:#343c4b; --accent:#8ca5ff; --accent-soft:#252e4d; --warn:#ffd27a; --warn-bg:#332b18; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.55; }}
main {{ max-width:1120px; margin:0 auto; padding:28px 18px 48px; }}
h1 {{ font-size:clamp(1.45rem,4vw,2.2rem); margin:0 0 6px; }} h2 {{ font-size:1.15rem; margin:0 0 12px; }}
.subtitle,.note,footer {{ color:var(--muted); }} section {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:18px; margin-top:16px; }}
.warning {{ background:var(--warn-bg); color:var(--warn); border-color:color-mix(in srgb,var(--warn) 30%,transparent); font-weight:600; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }}
.stat {{ border-left:3px solid var(--accent); padding:4px 10px; min-width:0; }} .stat-label {{ color:var(--muted); font-size:.82rem; }} .stat-value {{ font-size:1.05rem; overflow-wrap:anywhere; }}
.table-wrap {{ overflow-x:auto; }} table {{ width:100%; border-collapse:collapse; font-size:.9rem; }} th,td {{ padding:9px 10px; border-bottom:1px solid var(--border); text-align:left; vertical-align:top; }} th {{ color:var(--muted); font-weight:600; white-space:nowrap; }}
code {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; overflow-wrap:anywhere; }} .sequence {{ white-space:nowrap; }} .tag {{ display:inline-block; min-width:1.8em; text-align:center; padding:1px 6px; border-radius:999px; background:var(--accent-soft); color:var(--text); font-weight:700; }}
.metric-value {{ display:block; font-variant-numeric:tabular-nums; }} .meter {{ display:block; width:110px; max-width:100%; height:6px; margin-top:4px; background:var(--border); border-radius:999px; overflow:hidden; }} .meter>span {{ display:block; height:100%; background:var(--accent); }} .heuristic>span {{ opacity:.62; }}
details {{ border-top:1px solid var(--border); padding-top:10px; margin-top:10px; }} summary {{ cursor:pointer; font-weight:600; }} ol {{ padding-left:1.35rem; }} li+li {{ margin-top:7px; }}
footer {{ margin-top:22px; font-size:.82rem; }}
@media (max-width:560px) {{ main {{ padding:18px 10px 36px; }} section {{ padding:14px 12px; }} th,td {{ padding:8px 7px; }} }}
</style>
</head>
<body>
<main>
<header><h1>{m['title']}</h1><p class="subtitle">{_text(name)}</p></header>
<section class="warning" role="note">{m['model_only']}</section>
<section><h2>{m['summary']}</h2><div class="stats">
<div class="stat"><div class="stat-label">{m['job']}</div><div class="stat-value">{_text(name)}</div></div>
<div class="stat"><div class="stat-label">{m['route']}</div><div class="stat-value">{_text(route)}</div></div>
<div class="stat"><div class="stat-label">{m['status']}</div><div class="stat-value">{_text(run_status)}</div></div>
<div class="stat"><div class="stat-label">{m['models']}</div><div class="stat-value">{len(materialized_rows)}</div></div>
</div></section>
{_protein_table(job, m)}
{_motif_table(scan, m)}
{_peptide_tables(scan, m)}
{_confidence_table(materialized_rows, m)}
{_warning_section(job, scan, status, m)}
<section><h2>{m['how_to_read']}</h2><ol>{warning_items}</ol><p class="warning-text">{m['raw_warning']}</p></section>
<footer>{m['generated']}</footer>
</main>
</body>
</html>
"""


def write_html_report(
    job: Mapping[str, Any] | None,
    rows: Iterable[Mapping[str, Any]],
    destination: Path,
    *,
    scan: Mapping[str, Any] | None = None,
    status: Mapping[str, Any] | None = None,
    language: str | None = None,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        build_html_report(job, rows, scan=scan, status=status, language=language),
        encoding="utf-8",
    )
    return destination
