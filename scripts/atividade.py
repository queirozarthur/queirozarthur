"""
Gera atividade.svg com as contribuições do último ano,
no visual do card GitHubActivity (paleta calamansi).
Roda pelo GitHub Actions, ver .github/workflows/atividade.yml
"""
import base64
import json
import os
import urllib.request
from datetime import date

USUARIO = os.environ.get("USUARIO", "queirozarthur")
SAIDA = "atividade.svg"

CEL = 11
GAP = 3
PAD = 20
SEMANAS = 53

FUNDO = ["#8fa37d", "#5c7a67", "#39564a"]
CORES = ["#d9f2a6", "#b4e84c", "#8fc22f", "#5f8a14"]
NIVEL = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
FONTE = 'ui-rounded, "SF Pro Rounded", "Segoe UI", system-ui, sans-serif'

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
      commitContributionsByRepository(maxRepositories: 3) {
        repository { name owner { login } }
        contributions { totalCount }
      }
    }
  }
}
"""


def buscar():
    corpo = json.dumps({"query": QUERY, "variables": {"login": USUARIO}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=corpo,
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"]},
    )
    with urllib.request.urlopen(req) as r:
        res = json.load(r)
    if "errors" in res:
        raise SystemExit(res["errors"])

    col = res["data"]["user"]["contributionsCollection"]

    dias = []
    for sem in col["contributionCalendar"]["weeks"]:
        for d in sem["contributionDays"]:
            dias.append((d["date"], d["contributionCount"], NIVEL[d["contributionLevel"]]))

    repos = []
    for item in col["commitContributionsByRepository"]:
        rep = item["repository"]
        repos.append((rep["name"], rep["owner"]["login"], item["contributions"]["totalCount"]))

    return dias, repos


def avatar(dono):
    # repo de outra pessoa mostra a foto do dono, igual ao componente
    try:
        with urllib.request.urlopen(f"https://github.com/{dono}.png?size=64") as r:
            tipo = r.headers.get_content_type()
            return f"data:{tipo};base64," + base64.b64encode(r.read()).decode()
    except Exception:
        return None


def domingo(d):
    # 0 = domingo, igual ao calendário do GitHub
    return (d.weekday() + 1) % 7


def colunas(dias):
    ini = date.fromisoformat(dias[0][0])
    base = ini.toordinal() - domingo(ini)
    cols = {}
    for dt, qtd, niv in dias:
        d = date.fromisoformat(dt)
        cols.setdefault((d.toordinal() - base) // 7, []).append((d, qtd, niv))
    return [cols[c] for c in sorted(cols)][-SEMANAS:]


def rotulos(cols):
    # mês com menos de 3 semanas não ganha nome, senão encosta no próximo
    res = [None] * len(cols)
    ini = 0
    for i in range(1, len(cols) + 1):
        if i < len(cols) and cols[i][0][0].month == cols[ini][0][0].month:
            continue
        if i - ini >= 3:
            res[ini] = MESES[cols[ini][0][0].month - 1]
        ini = i
    return res


def esc(txt):
    return txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def montar(dias, repos, fotos):
    cols = colunas(dias)
    meses = rotulos(cols)
    total = sum(q for c in cols for _, q, _ in c)
    passo = CEL + GAP

    larg = PAD * 2 + len(cols) * passo - GAP
    y_mes = 60
    y_grade = y_mes + 12 + GAP
    fim = y_grade + 7 * passo - GAP

    y_p = fim + 16
    alt_p = 44 + len(repos) * 40 + 6
    alt = y_p + alt_p + 8 if repos else fim + PAD

    varrida = (len(cols) - 1) * 0.012 + 0.2
    palavra = "contribuição" if total == 1 else "contribuições"
    titulo = f"{total:,}".replace(",", ".") + f" {palavra} no último ano"

    s = []
    s.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{larg}" height="{alt}" '
        f'viewBox="0 0 {larg} {alt}" role="img" aria-label="{titulo}">'
    )
    s.append(f"<title>{titulo}</title>")
    s.append(f"""<style>
text {{ font-family: {FONTE}; fill: #fff }}
.c {{ animation: entra .2s cubic-bezier(.22,1,.36,1) both; animation-delay: var(--d);
      transform-box: fill-box; transform-origin: center }}
.m {{ animation: foco .45s cubic-bezier(.22,1,.36,1) {varrida:.2f}s both }}
.p {{ animation: sobe .62s cubic-bezier(.34,1.4,.64,1) {varrida + .1:.2f}s both }}
@keyframes entra {{ from {{ opacity: 0; transform: scale(.4) }} }}
@keyframes foco {{ from {{ opacity: 0; filter: blur(6px) }} }}
@keyframes sobe {{ from {{ opacity: 0; transform: translate(16px, 16px) }} }}
@media (prefers-reduced-motion: reduce) {{ .c, .m, .p {{ animation: none }} }}
</style>""")

    s.append('<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">')
    for i, cor in enumerate(FUNDO):
        s.append(f'<stop offset="{i / 2}" stop-color="{cor}"/>')
    s.append("</linearGradient>")
    for i in range(len(repos)):
        cy = y_p + 44 + i * 40 + 20
        s.append(f'<clipPath id="a{i}"><circle cx="38" cy="{cy}" r="14"/></clipPath>')
    s.append("</defs>")

    s.append(f'<rect width="{larg}" height="{alt}" rx="28" fill="url(#g)"/>')
    s.append(f'<text x="{PAD + 6}" y="{PAD + 17}" font-size="16" font-weight="700">{titulo}</text>')

    s.append('<g class="m">')
    for i, mes in enumerate(meses):
        if mes:
            s.append(
                f'<text x="{PAD + i * passo}" y="{y_mes + 9}" font-size="10" '
                f'fill-opacity=".45">{mes}</text>'
            )
    s.append("</g>")

    for i, col in enumerate(cols):
        s.append(f'<g style="--d:{i * 0.012:.3f}s">')
        x = PAD + i * passo
        for d, qtd, niv in col:
            y = y_grade + domingo(d) * passo
            if niv:
                cor = f'fill="{CORES[niv - 1]}"'
            else:
                cor = 'fill="#fff" fill-opacity=".15"'
            dica = f"{qtd} em {d.strftime('%d/%m/%Y')}"
            s.append(
                f'<rect class="c" x="{x}" y="{y}" width="{CEL}" height="{CEL}" rx="3" {cor}>'
                f"<title>{dica}</title></rect>"
            )
        s.append("</g>")

    if repos:
        s.append('<g class="p">')
        s.append(
            f'<rect x="8" y="{y_p}" width="{larg - 16}" height="{alt_p}" rx="18" '
            f'fill="#000" fill-opacity=".65" stroke="#fff" stroke-opacity=".25"/>'
        )
        s.append(
            f'<text x="24" y="{y_p + 27}" font-size="14" font-weight="500">'
            f"Mais contribuições em:</text>"
        )
        for i, (nome, dono, qtd) in enumerate(repos):
            y0 = y_p + 44 + i * 40
            cy = y0 + 20
            s.append(
                f'<circle cx="38" cy="{cy}" r="15" fill="none" stroke="#fff" '
                f'stroke-opacity=".2" stroke-width="2"/>'
            )
            foto = fotos.get(dono)
            if foto:
                s.append(
                    f'<image href="{foto}" x="24" y="{cy - 14}" width="28" height="28" '
                    f'clip-path="url(#a{i})"/>'
                )
            else:
                s.append(f'<circle cx="38" cy="{cy}" r="14" fill="#fff" fill-opacity=".25"/>')
                s.append(
                    f'<text x="38" y="{cy + 4}" font-size="11" font-weight="500" '
                    f'text-anchor="middle">{esc(nome[0].upper())}</text>'
                )
            s.append(f'<text x="64" y="{cy + 5}" font-size="14">{esc(nome)}</text>')
            s.append(
                f'<text x="{larg - 32}" y="{cy + 5}" font-size="14" text-anchor="end" '
                f'fill-opacity=".85">{qtd}</text>'
            )
        s.append("</g>")

    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    dias, repos = buscar()
    fotos = {}
    for _, dono, _ in repos:
        if dono.lower() != USUARIO.lower() and dono not in fotos:
            fotos[dono] = avatar(dono)

    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(montar(dias, repos, fotos))
    print("ok:", SAIDA)
