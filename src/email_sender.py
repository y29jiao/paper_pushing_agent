"""Gmail SMTP email sender with HTML templates."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def build_email_html(
    profile_results: dict[str, list[dict]],
    push_time: str,
    summary_language: str = "zh",
) -> str:
    """
    Build HTML email content from profile results.

    Args:
        profile_results: Dict mapping profile_name -> list of enriched paper dicts
        push_time: Human-readable push time string
        summary_language: "zh" or "en"
    """
    html_parts = [_email_header(push_time, summary_language)]

    for profile_name, papers in profile_results.items():
        html_parts.append(_profile_section(profile_name, papers, summary_language))

    html_parts.append(_email_footer(summary_language))

    return "\n".join(html_parts)


def _email_header(push_time: str, summary_language: str) -> str:
    title = "📚 Paper Agent Push" if summary_language == "en" else "📚 Paper Agent 推送"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background-color: #f4f4f7;
    margin: 0;
    padding: 20px;
    color: #333;
    line-height: 1.6;
  }}
  .container {{
    max-width: 700px;
    margin: 0 auto;
    background: #fff;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }}
  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: #fff;
    padding: 30px;
    text-align: center;
  }}
  .header h1 {{
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }}
  .header .date {{
    margin-top: 8px;
    font-size: 14px;
    opacity: 0.8;
  }}
  .profile-section {{
    padding: 0 30px;
  }}
  .profile-title {{
    font-size: 18px;
    font-weight: 700;
    color: #0f3460;
    border-bottom: 2px solid #e94560;
    padding: 20px 0 8px 0;
    margin-top: 10px;
  }}
  .paper-card {{
    border: 1px solid #e8e8ed;
    border-radius: 8px;
    padding: 20px;
    margin: 16px 0;
    transition: box-shadow 0.2s;
  }}
  .paper-card:hover {{
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  .paper-title {{
    font-size: 16px;
    font-weight: 600;
    color: #1a1a2e;
    margin: 0 0 8px 0;
  }}
  .paper-title a {{
    color: #0f3460;
    text-decoration: none;
  }}
  .paper-title a:hover {{
    text-decoration: underline;
    color: #e94560;
  }}
  .paper-meta {{
    font-size: 13px;
    color: #666;
    margin-bottom: 12px;
  }}
  .paper-meta span {{
    margin-right: 12px;
  }}
  .tag {{
    display: inline-block;
    background: #e8f0fe;
    color: #1967d2;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 4px;
  }}
  .tag.venue {{
    background: #fce8e6;
    color: #c5221f;
  }}
  .section-label {{
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #999;
    margin: 12px 0 4px 0;
  }}
  .relevance {{
    background: #f0fdf4;
    border-left: 3px solid #22c55e;
    padding: 8px 12px;
    font-size: 14px;
    color: #15803d;
    margin: 8px 0;
    border-radius: 0 4px 4px 0;
  }}
  .summary {{
    font-size: 14px;
    color: #333;
    margin: 8px 0;
    padding: 10px 12px;
    background: #fafafa;
    border-radius: 6px;
  }}
  .abstract {{
    font-size: 13px;
    color: #555;
    margin: 8px 0;
    padding: 10px 12px;
    background: #f8f8fa;
    border-radius: 6px;
    max-height: 200px;
    overflow: hidden;
  }}
  .footer {{
    text-align: center;
    padding: 20px 30px;
    font-size: 12px;
    color: #999;
    border-top: 1px solid #eee;
    margin-top: 20px;
  }}
  .no-papers {{
    text-align: center;
    padding: 30px;
    color: #999;
    font-style: italic;
  }}
  .paper-number {{
    display: inline-block;
    width: 24px;
    height: 24px;
    background: #0f3460;
    color: #fff;
    border-radius: 50%;
    text-align: center;
    line-height: 24px;
    font-size: 13px;
    font-weight: 600;
    margin-right: 8px;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{title}</h1>
    <div class="date">{push_time}</div>
  </div>
"""


def _profile_section(profile_name: str, papers: list[dict], summary_language: str) -> str:
    no_papers_text = "No new matching papers were found this time" if summary_language == "en" else "本次未找到符合要求的新论文"
    abstract_label = "📋 Abstract"
    summary_label = "📝 Summary" if summary_language == "en" else "📝 中文总结"
    relevance_label = "💡 Why it is recommended" if summary_language == "en" else "💡 推荐理由"
    cite_prefix = "📊 Citations: " if summary_language == "en" else "📊 引用: "

    html = f"""
  <div class="profile-section">
    <div class="profile-title">📂 {profile_name}</div>
"""
    if not papers:
        html += f'    <div class="no-papers">{no_papers_text}</div>\n'
    else:
        for i, paper in enumerate(papers, 1):
            venue_tag = f'<span class="tag venue">{paper["venue"]}</span>' if paper.get("venue") else ""
            year_tag = f'<span class="tag">{paper["year"]}</span>' if paper.get("year") else ""
            cite_text = f'{cite_prefix}{paper["citation_count"]}' if paper.get("citation_count") is not None else ""
            score_text = f' | ⭐ Review Score: {paper["score"]}' if paper.get("score") is not None else ""
            summary_text = paper.get("summary_text") or paper.get("summary_zh", "")

            # Authors (first 3)
            authors = paper.get("authors", [])
            author_text = ", ".join(authors[:3])
            if len(authors) > 3:
                author_text += " et al."

            url = paper.get("url", "#")

            html += f"""
    <div class="paper-card">
      <div class="paper-title">
        <span class="paper-number">{i}</span>
        <a href="{url}" target="_blank">{paper['title']}</a>
      </div>
      <div class="paper-meta">
        {venue_tag} {year_tag}
        <span>{cite_text}{score_text}</span>
      </div>
      <div class="paper-meta" style="color:#888;">{author_text}</div>

      <div class="section-label">{abstract_label}</div>
      <div class="abstract">{paper.get('abstract', '')[:800]}{'...' if len(paper.get('abstract', '')) > 800 else ''}</div>

      <div class="section-label">{summary_label}</div>
      <div class="summary">{summary_text}</div>

      <div class="section-label">{relevance_label}</div>
      <div class="relevance">{paper.get('relevance_reason', '')}</div>
    </div>
"""

    html += "  </div>\n"
    return html


def _email_footer(summary_language: str) -> str:
    footer_note = "This email was automatically generated by Paper Agent" if summary_language == "en" else "此邮件由 Paper Agent 自动生成"
    return """
  <div class="footer">
    Paper Agent — Powered by GPT · Semantic Scholar · OpenReview · OpenAlex<br>
    """ + footer_note + """
  </div>
</div>
</body>
</html>"""


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    gmail_address: str,
    gmail_app_password: str,
):
    """Send an HTML email via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = gmail_address
    msg["To"] = to_email
    msg["Subject"] = subject

    # Plain text fallback
    plain_text = "Paper Agent push — please use an HTML-capable email client to view this message."
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.send_message(msg)

    print(f"[Email] Sent to {to_email}")
