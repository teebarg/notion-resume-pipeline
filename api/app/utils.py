from fastapi.responses import HTMLResponse

def render_error_page(
    title: str,
    message: str,
    status_code: int,
) -> HTMLResponse:
    return HTMLResponse(
        content=f"""
        <html>
            <body style="
                font-family:sans-serif;
                display:flex;
                align-items:center;
                justify-content:center;
                background:#fafafa;
            ">
                <div style="text-align:center">
                    <h1>{title}</h1>
                    <p>{message}</p>
                </div>
            </body>
        </html>
        """,
        status_code=status_code,
    )