import flet as ft
import flet.canvas as cv
import time
import asyncio
import datetime
import sqlite3
import os
import sys

def main(page: ft.Page):
    # --- CONFIGURAÇÕES DA PÁGINA ---
    page.title = "OnePercent - Deep Work"
    page.window.width = 420
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0 
    page.bgcolor = "#050A15" 

    # --- CARREGANDO SUA FONTE CUSTOMIZADA (OPCIONAL) ---
    page.fonts = {
        "FonteCustomizada": "assets/fonte.ttf" 
    }

    # --- INICIALIZAÇÃO SEGURA DO BANCO DE DADOS (LOCAL) ---
    if page.platform == ft.PagePlatform.ANDROID or page.platform == ft.PagePlatform.IOS:
        caminho_base = os.environ.get("HOME", ".")
    else:
        if getattr(sys, 'frozen', False):
            caminho_base = os.path.dirname(sys.executable)
        else:
            caminho_base = os.path.dirname(os.path.abspath(__file__))
            
    db_path = os.path.join(caminho_base, "onepercent.db")
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tarefas (id INTEGER PRIMARY KEY AUTOINCREMENT, dia TEXT, categoria TEXT, texto TEXT, concluida INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS agua (dia TEXT PRIMARY KEY, atual REAL, meta REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS metricas (id INTEGER PRIMARY KEY, peso REAL, altura REAL, meta REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT)''')
    conn.commit()

    # --- VARIÁVEIS GLOBAIS ---
    estado_timer = {"rodando": False, "segundos": 0} 
    
    checks_treinos = []
    checks_trabalho = []
    checks_estudos = []
    checks_casa = []
    checks_familia = []
    
    estado_gamificacao = {"ofensiva": 1, "nivel": 1, "dias_cumpridos_hoje": False, "dias_cumpridos_semana": 0}

    hoje = datetime.datetime.now()
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    texto_data = f"{hoje.day} de {meses[hoje.month - 1]} de {hoje.year}"
    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    dia_selecionado = dias_semana[hoje.weekday()]

    # --- FUNÇÃO DO GRÁFICO DE RADAR GAMIFICADO (GRADIENTE RADIAL) ---
    def criar_bloco_radar_gamificado(tamanho):
        cx, cy = tamanho / 2, tamanho / 2
        R = tamanho / 2 - 25 

        def get_hexagon_points(raio_hex):
            p = []
            import math
            for i in range(6):
                angle = math.radians(60 * i + 30) 
                p.append(cv.Path.LineTo(cx + raio_hex * math.cos(angle), cy + raio_hex * math.sin(angle)))
            p.append(cv.Path.LineTo(p[0].x, p[0].y)) 
            return p

        # 1. Estrutura da Teia (Cinza Concêntrico)
        interior_path_elements = []
        for pct in [0.2, 0.4, 0.6, 0.8]:
            raio_hex = R * pct
            points = get_hexagon_points(raio_hex)
            interior_path_elements.append(cv.Path.MoveTo(points[0].x, points[0].y))
            interior_path_elements.extend(points[1:])

        forma_interna = cv.Path(interior_path_elements, paint=ft.Paint(style=ft.PaintingStyle.STROKE, color="#55AAAAAA", stroke_width=1))

        # 2. Hexágono Externo (Vermelho)
        externo_points = get_hexagon_points(R)
        forma_externa = cv.Path([cv.Path.MoveTo(externo_points[0].x, externo_points[0].y)] + externo_points[1:], paint=ft.Paint(style=ft.PaintingStyle.STROKE, color=ft.Colors.RED, stroke_width=2))

        # 3. Linhas de Eixo (Cinza)
        eixo_path_elements = []
        for p in externo_points[:-1]:
            eixo_path_elements.append(cv.Path.MoveTo(cx, cy))
            eixo_path_elements.append(cv.Path.LineTo(p.x, p.y))
        forma_eixos = cv.Path(eixo_path_elements, paint=ft.Paint(style=ft.PaintingStyle.STROKE, color="#55AAAAAA", stroke_width=1))

        # 4. PREENCHIMENTO: Gradiente Radial Roxo pro Amarelo com 75% de Opacidade (Código Hexadecimal BF)
        gradiente_radar = ft.PaintRadialGradient(
            center=ft.Offset(cx, cy),
            radius=R,
            colors=["#BF9C27B0", "#BFFFEB3B"] # BF = 75% Opacidade, Roxo no centro e Amarelo na borda
        )
        forma_dinamica = cv.Path([], paint=ft.Paint(style=ft.PaintingStyle.FILL, gradient=gradiente_radar))

        # IMPORTANTE: Coloquei a forma_dinamica PRIMEIRO, assim as linhas da teia ficam POR CIMA do gradiente!
        canvas_radar = cv.Canvas([forma_dinamica, forma_interna, forma_eixos, forma_externa], width=tamanho, height=tamanho)

        # 5. Texto Central
        texto_central_ui = ft.Text("0%", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

        def atualizar_progresso(e=None):
            def calc_pct(lista):
                return sum(1 for c in lista if c.value) / len(lista) if len(lista) > 0 else 0

            pct_treinos, pct_trab, pct_estudos = calc_pct(checks_treinos), calc_pct(checks_trabalho), calc_pct(checks_estudos)
            pct_casa, pct_familia = calc_pct(checks_casa), calc_pct(checks_familia)
            
            meta_agua = float(agua_meta_input.value.replace(',', '.')) if agua_meta_input.value else 3.0
            pct_agua = min(1.0, agua_atual / meta_agua) if meta_agua > 0 else 0

            r_tre, r_agu, r_tra = R * max(0.05, pct_treinos), R * max(0.05, pct_agua), R * max(0.05, pct_trab)
            r_est, r_cas, r_fam = R * max(0.05, pct_estudos), R * max(0.05, pct_casa), R * max(0.05, pct_familia)
            
            p_dinamicos = [r_tre, r_agu, r_tra, r_est, r_cas, r_fam]
            dinamico_points = []
            import math
            for i, raio in enumerate(p_dinamicos):
                angle = math.radians(60 * i + 30) 
                dinamico_points.append(cv.Path.LineTo(cx + raio * math.cos(angle), cy + raio * math.sin(angle)))
            dinamico_points.append(cv.Path.LineTo(dinamico_points[0].x, dinamico_points[0].y)) 

            forma_dinamica.elements = [cv.Path.MoveTo(dinamico_points[0].x, dinamico_points[0].y)] + dinamico_points[1:]

            total_items = len(checks_treinos) + len(checks_trabalho) + len(checks_estudos) + len(checks_casa) + len(checks_familia) + 1 
            concluidas = sum(1 for c in checks_treinos + checks_trabalho + checks_estudos + checks_casa + checks_familia if c.value)
            if pct_agua >= 1.0: concluidas += 1

            geral = (concluidas / total_items) if total_items > 0 else 0
            texto_central_ui.value = f"{int(geral * 100)}%"
            page.update()

        # Rótulos
        rotulos_radar = ft.Stack([
            ft.Container(canvas_radar, alignment=ft.Alignment(0, 0)),
            ft.Container(ft.Text("Treinos", size=9, weight="bold", color="#FF3D00"), top=5, left=cx-20),
            ft.Container(ft.Text("Água", size=9, weight="bold", color="#00E5FF"), top=35, right=5),
            ft.Container(ft.Text("Trab", size=9, weight="bold", color="#3A86FF"), bottom=35, right=5),
            ft.Container(ft.Text("Estudos", size=9, weight="bold", color="#FFBE0B"), bottom=5, left=cx-20),
            ft.Container(ft.Text("Casa", size=9, weight="bold", color="#9CA3AF"), bottom=35, left=5),
            ft.Container(ft.Text("Família", size=9, weight="bold", color="#F472B6"), top=35, left=5),
        ], width=tamanho, height=tamanho)

        bloco_radar_final = ft.Stack([
            ft.Container(rotulos_radar, alignment=ft.Alignment(0, 0)),
            ft.Container(texto_central_ui, width=tamanho, height=tamanho, alignment=ft.Alignment(0, 0)),
        ], width=tamanho, height=tamanho)

        return bloco_radar_final, atualizar_progresso

    # --- POP-UP DAS MÉTRICAS ---
    p_input = ft.TextField(label="Peso(kg)", label_style=ft.TextStyle(size=12), text_size=12, width=75, dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)
    a_input = ft.TextField(label="Alt.(cm)", label_style=ft.TextStyle(size=12), text_size=12, width=75, dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)
    res_imc = ft.Text("--", size=14, weight=ft.FontWeight.BOLD, color="#39FF14") 
    m_input = ft.TextField(label="Meta(kg)", label_style=ft.TextStyle(size=12), text_size=12, width=75, dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)
    res_meta = ft.Text("--", size=14, weight=ft.FontWeight.BOLD, color="#FFBE0B") 

    def calc_imc(e):
        try: res_imc.value = f"{(float(p_input.value.replace(',', '.')) / ((float(a_input.value.replace(',', '.'))/100) ** 2)):.1f}"; page.update()
        except: pass

    def calc_meta(e):
        try: res_meta.value = f"{(float(p_input.value.replace(',', '.')) - float(m_input.value.replace(',', '.'))):.1f}kg" if (float(p_input.value.replace(',', '.')) - float(m_input.value.replace(',', '.'))) > 0 else "Alcançada!"; page.update()
        except: pass

    def salvar_metricas(e):
        try:
            peso = float(p_input.value.replace(',', '.')) if p_input.value else 0.0
            altura = float(a_input.value.replace(',', '.')) if a_input.value else 0.0
            meta = float(m_input.value.replace(',', '.')) if m_input.value else 0.0
            c.execute("INSERT OR REPLACE INTO metricas (id, peso, altura, meta) VALUES (1, ?, ?, ?)", (peso, altura, meta))
            conn.commit()
        except: pass
        calc_imc(None)
        calc_meta(None)
        modal_metricas.open = False
        page.update()

    def fechar_modal_metricas(e):
        modal_metricas.open = False
        page.update()

    def abrir_modal_metricas(e):
        modal_metricas.open = True
        page.update()

    modal_metricas = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.Icons.FITNESS_CENTER, color="#39FF14"), ft.Text("Status do Personagem", color=ft.Colors.WHITE, size=18, weight="bold")]),
        content=ft.Container(
            width=290, 
            content=ft.Column([
                ft.Text("Atualize suas medidas e metas.", size=11, color="#9CA3AF"),
                ft.Container(height=8),
                ft.Row([p_input, a_input, ft.Row([ft.IconButton(ft.Icons.CALCULATE, icon_color="#39FF14", icon_size=16, on_click=calc_imc, padding=0), res_imc], spacing=0)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([m_input, ft.Row([ft.IconButton(ft.Icons.TRACK_CHANGES, icon_color="#FFBE0B", icon_size=16, on_click=calc_meta, padding=0), res_meta], spacing=0)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], tight=True, spacing=10) 
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=fechar_modal_metricas, style=ft.ButtonStyle(color="#9CA3AF")),
            ft.ElevatedButton("Salvar Status", on_click=salvar_metricas, bgcolor="#00E5FF", color=ft.Colors.BLACK)
        ],
        bgcolor="#111827", shape=ft.RoundedRectangleBorder(radius=16)
    )
    page.overlay.append(modal_metricas)

    # --- POP-UP DE ANOTAÇÕES ---
    lista_notas_ui = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    input_nota = ft.TextField(hint_text="Escreva uma nova anotação...", expand=True, dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT, text_size=13)

    def carregar_notas():
        lista_notas_ui.controls.clear()
        c.execute("SELECT id, texto FROM notas")
        for nid, txt in c.fetchall():
            lista_notas_ui.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.SUBDIRECTORY_ARROW_RIGHT, color="#39FF14", size=14),
                    ft.Text(txt, expand=True, size=13, color=ft.Colors.WHITE),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#EF4444", icon_size=18, on_click=lambda e, id=nid: remover_nota(id), padding=0)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)
            )
        page.update()

    def add_nota(e):
        if input_nota.value:
            c.execute("INSERT INTO notas (texto) VALUES (?)", (input_nota.value,))
            conn.commit()
            input_nota.value = ""
            carregar_notas()
            input_nota.focus()

    def remover_nota(nid):
        c.execute("DELETE FROM notas WHERE id=?", (nid,))
        conn.commit()
        carregar_notas()

    def fechar_modal_notas(e):
        modal_notas.open = False
        page.update()

    def abrir_modal_notas(e):
        carregar_notas()
        modal_notas.open = True
        page.update()

    modal_notas = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.Icons.EDIT_NOTE, color="#39FF14"), ft.Text("Anotações", color=ft.Colors.WHITE, size=18, weight="bold")]),
        content=ft.Container(
            width=300, height=350,
            content=ft.Column([
                ft.Row([
                    input_nota, 
                    ft.IconButton(ft.Icons.ADD_BOX, icon_color="#39FF14", icon_size=35, on_click=add_nota, padding=0)
                ]),
                ft.Divider(color="#374151"),
                lista_notas_ui
            ])
        ),
        actions=[
            ft.ElevatedButton("Fechar", on_click=fechar_modal_notas, bgcolor="#1F2937", color=ft.Colors.WHITE)
        ],
        bgcolor="#111827", shape=ft.RoundedRectangleBorder(radius=16)
    )
    page.overlay.append(modal_notas)

    # --- POP-UP DE ALERTA DE TREINO (O ALARME) ---
    def fechar_alerta_treino(e):
        modal_alerta_treino.open = False
        page.update()

    texto_alerta_treino = ft.Text("", size=16, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)
    
    modal_alerta_treino = ft.AlertDialog(
        modal=False,
        title=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#FF3D00", size=30), ft.Text("HORA DO TREINO!", color="#FF3D00", weight="bold")], alignment=ft.MainAxisAlignment.CENTER),
        content=ft.Container(width=250, content=texto_alerta_treino, alignment=ft.Alignment(0, 0)),
        actions=[ft.ElevatedButton("BORA LÁ!", on_click=fechar_alerta_treino, bgcolor="#00E5FF", color=ft.Colors.BLACK)],
        actions_alignment=ft.MainAxisAlignment.CENTER,
        bgcolor="#111827", shape=ft.RoundedRectangleBorder(radius=16)
    )
    page.overlay.append(modal_alerta_treino)

    def disparar_alarme_na_tela(exercicios):
        texto_alerta_treino.value = f"Seu horário chegou.\nPrepare-se para o treino:\n\n{exercicios}"
        modal_alerta_treino.open = True
        page.update()

    c.execute("SELECT peso, altura, meta FROM metricas WHERE id=1")
    row_metrics = c.fetchone()
    if row_metrics:
        p_input.value = str(row_metrics[0])
        a_input.value = str(row_metrics[1])
        m_input.value = str(row_metrics[2])
        calc_imc(None)
        calc_meta(None)

    # --- EMBLEMAS E CABEÇALHO REESTRUTURADO ---
    badges_gamificacao = ft.Row([
        ft.Container(content=ft.Row([ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#FFBE0B", size=14), ft.Text("1 Dia", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]), bgcolor="#1F2937", padding=ft.padding.only(left=6, right=6, top=2, bottom=2), border_radius=12),
        ft.Container(content=ft.Row([ft.Icon(ft.Icons.ROCKET_LAUNCH, color="#00E5FF", size=14), ft.Text("Nível 1", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]), bgcolor="#1F2937", padding=ft.padding.only(left=6, right=6, top=2, bottom=2), border_radius=12)
    ], spacing=5)

    btn_anotacoes = ft.TextButton("Anotações", icon=ft.Icons.EDIT_NOTE, style=ft.ButtonStyle(color="#39FF14"), on_click=abrir_modal_notas)

    arte_cabecalho = cv.Canvas(
        height=210, 
        shapes=[
            cv.Path(elements=[cv.Path.MoveTo(0, 80), cv.Path.CubicTo(100, 10, 200, 150, 420, 60)], paint=ft.Paint(color="#4400E5FF", style=ft.PaintingStyle.STROKE, stroke_width=4)),
            cv.Path(elements=[cv.Path.MoveTo(0, 120), cv.Path.CubicTo(150, 200, 250, 20, 420, 100)], paint=ft.Paint(color="#44FFBE0B", style=ft.PaintingStyle.STROKE, stroke_width=4)),
            cv.Path(elements=[cv.Path.MoveTo(0, 100), cv.Path.CubicTo(120, 120, 300, 60, 420, 140)], paint=ft.Paint(color="#11FFFFFF", style=ft.PaintingStyle.STROKE, stroke_width=2))
        ]
    )

    coluna_textos = ft.Container(
        height=150, 
        expand=True,
        content=ft.Column([
            ft.Row([
                ft.IconButton(icon=ft.Icons.PERSON, icon_color=ft.Colors.WHITE, icon_size=18, width=24, height=24, on_click=abrir_modal_metricas, tooltip="Status", padding=0),
                ft.Text(texto_data, size=12, color="#00E5FF", weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.START, spacing=5), 
            
            ft.Container(height=10),
            
            ft.Column([
                ft.Text("Evolua 1%", size=24, weight=ft.FontWeight.W_900, color=ft.Colors.WHITE, font_family="Impact, Arial Black, sans-serif", text_align=ft.TextAlign.CENTER),
                ft.Text("todos os dias!", size=24, weight=ft.FontWeight.W_900, color=ft.Colors.WHITE, font_family="Impact, Arial Black, sans-serif", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Container(height=4),
            
            ft.Text("A constância constrói resultados.", size=12, color="#D1D5DB"),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN) 
    )

    bloco_radar_final, atualizar_progresso = criar_bloco_radar_gamificado(150)

    bloco_superior = ft.Row([
        coluna_textos,
        ft.Container(bloco_radar_final, margin=ft.margin.only(right=25))
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)

    bloco_inferior = ft.Row([
        badges_gamificacao,
        btn_anotacoes
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    cabecalho = ft.Stack([
        arte_cabecalho, 
        ft.Container(
            padding=ft.padding.only(top=20, left=15, right=15, bottom=0),
            content=ft.Column([
                bloco_superior,
                ft.Container(height=10), 
                bloco_inferior
            ], spacing=0)
        )
    ])

    # --- MÓDULO DE ÁGUA ---
    agua_atual = 0.0 
    agua_meta_input = ft.TextField(value="3.0", width=60, dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)
    txt_agua_atual = ft.Text("0.0L", size=24, weight=ft.FontWeight.BOLD, color="#00E5FF")
    barra_agua = ft.ProgressBar(value=0, color="#00E5FF", bgcolor="#374151", height=8)

    def beber_agua(e):
        nonlocal agua_atual
        try: meta = float(agua_meta_input.value.replace(',', '.'))
        except: meta = 3.0
        if meta <= 0: meta = 3.0
        agua_atual += 0.25
        if agua_atual >= meta: agua_atual = meta
        
        c.execute("INSERT OR REPLACE INTO agua (dia, atual, meta) VALUES (?, ?, ?)", (dia_selecionado, agua_atual, meta))
        conn.commit()
        
        txt_agua_atual.value = f"{agua_atual:.2f}L"
        barra_agua.value = agua_atual / meta
        atualizar_progresso()

    def criar_cartao(titulo, conteudo, icone, cor_borda):
        return ft.Container(
            content=ft.Column([ft.Row([ft.Icon(icone, color=cor_borda), ft.Text(titulo, size=16, weight="bold", color=ft.Colors.WHITE)]), ft.Divider(color="#374151"), conteudo]), 
            bgcolor="#99111827", border_radius=16, padding=20, margin=ft.margin.only(bottom=15), border=ft.border.all(1, cor_borda)
        )

    cartao_agua = criar_cartao("Hidratação", ft.Column([ft.Row([ft.Column([ft.Text("Meta (L)", size=12, color="#9CA3AF"), agua_meta_input]), txt_agua_atual, ft.ElevatedButton("250ml", icon=ft.Icons.ADD, on_click=beber_agua, bgcolor="#00E5FF", color=ft.Colors.BLACK)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), barra_agua]), ft.Icons.WATER_DROP, "#00E5FF")

    # --- TAREFAS DINÂMICAS COMUNS ---
    coluna_treinos, coluna_trab, coluna_estudos, coluna_casa, coluna_familia = ft.Column(), ft.Column(), ft.Column(), ft.Column(), ft.Column()

    def criar_tarefa_ui(texto, coluna_destino, lista_checks, cor, categoria, task_id=None, concluida=False):
        if task_id is None:
            c.execute("INSERT INTO tarefas (dia, categoria, texto, concluida) VALUES (?, ?, ?, 0)", (dia_selecionado, categoria, texto))
            conn.commit()
            task_id = c.lastrowid

        chk = ft.Checkbox(label=texto, value=concluida, fill_color="#39FF14" if concluida else cor)
        lista_checks.append(chk)

        def on_check(e):
            chk.fill_color = "#39FF14" if chk.value else cor
            chk.update()
            c.execute("UPDATE tarefas SET concluida=? WHERE id=?", (int(chk.value), task_id))
            conn.commit()
            atualizar_progresso()

        chk.on_change = on_check

        def remover_tarefa(e):
            c.execute("DELETE FROM tarefas WHERE id=?", (task_id,))
            conn.commit()
            lista_checks.remove(chk)
            coluna_destino.controls.remove(linha)
            atualizar_progresso()

        linha = ft.Row([
            ft.Container(chk, expand=True), 
            ft.IconButton(icon=ft.Icons.DELETE_ROUNDED, icon_color="#EF4444", icon_size=20, on_click=remover_tarefa)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START)
        
        coluna_destino.controls.append(linha)
        atualizar_progresso()

    def comp_nova_tarefa(coluna_destino, lista_checks, dica, cor, categoria):
        campo = ft.TextField(hint_text=dica, expand=True, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        def add(e):
            if campo.value: criar_tarefa_ui(campo.value, coluna_destino, lista_checks, cor, categoria); campo.value = ""; page.update()
        return ft.Row([campo, ft.IconButton(icon=ft.Icons.ADD_BOX, icon_color=cor, icon_size=35, on_click=add)])

    # --- O FORMULÁRIO DE TREINOS ---
    hora_temp = {"selecionada": ""}

    def on_time_change(e):
        if time_picker.value:
            h = f"{time_picker.value.hour:02d}:{time_picker.value.minute:02d}"
            hora_temp["selecionada"] = h
            btn_abrir_relogio.icon = ft.Icons.ALARM_ON
            btn_abrir_relogio.icon_color = "#39FF14"
            txt_hora_badge.value = h
            page.update()

    time_picker = ft.TimePicker(
        confirm_text="Confirmar",
        error_invalid_text="Hora inválida",
        help_text="Selecione o horário do treino",
        on_change=on_time_change
    )
    page.overlay.append(time_picker)

    btn_abrir_relogio = ft.IconButton(icon=ft.Icons.ALARM_ADD, icon_color="#9CA3AF", tooltip="Definir Alarme", icon_size=20, on_click=lambda _: setattr(time_picker, 'open', True) or page.update())
    txt_hora_badge = ft.Text("", size=11, color="#39FF14", weight="bold")

    def comp_novo_treino(cor):
        campo_titulo = ft.TextField(hint_text="Título (Ex: Pull, Legs)", text_size=14, expand=True, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        campo_exercicio = ft.TextField(hint_text="Exercício (Ex: Afundo)", text_size=14, expand=True, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        campo_reps = ft.TextField(hint_text="Reps/Séries", text_size=12, expand=1, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        campo_peso = ft.TextField(hint_text="Peso (kg)", text_size=12, expand=1, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        
        def add(e):
            if campo_titulo.value and campo_exercicio.value:
                h_salvar = hora_temp["selecionada"]
                texto_final = f"{campo_titulo.value}|||{campo_exercicio.value}|||{campo_reps.value}|||{campo_peso.value}|||{h_salvar}"
                    
                c.execute("INSERT INTO tarefas (dia, categoria, texto, concluida) VALUES (?, ?, ?, 0)", (dia_selecionado, "treinos", texto_final))
                conn.commit()
                
                campo_exercicio.value = ""
                campo_reps.value = ""
                campo_peso.value = ""
                carregar_dados_do_dia()
                page.update()
                campo_exercicio.focus() 
                
        return ft.Column([
            campo_titulo,
            campo_exercicio,
            ft.Row([
                campo_reps, 
                campo_peso, 
                ft.Row([btn_abrir_relogio, txt_hora_badge], spacing=0),
                ft.IconButton(icon=ft.Icons.ADD_BOX, icon_color=cor, icon_size=35, on_click=add, padding=ft.padding.only(top=8))
            ])
        ], spacing=5)

    def on_check_treino(e, tid, c_obj):
        c_obj.fill_color = "#39FF14" if c_obj.value else "#FF3D00"
        c_obj.update()
        c.execute("UPDATE tarefas SET concluida=? WHERE id=?", (int(c_obj.value), tid))
        conn.commit()
        atualizar_progresso()

    def remover_treino(e, tid):
        c.execute("DELETE FROM tarefas WHERE id=?", (tid,))
        conn.commit()
        carregar_dados_do_dia()
        page.update()

    def carregar_dados_do_dia():
        nonlocal agua_atual
        
        coluna_treinos.controls.clear()
        coluna_trab.controls.clear()
        coluna_estudos.controls.clear()
        coluna_casa.controls.clear()
        coluna_familia.controls.clear()
        checks_treinos.clear()
        checks_trabalho.clear()
        checks_estudos.clear()
        checks_casa.clear()
        checks_familia.clear()

        c.execute("SELECT atual, meta FROM agua WHERE dia=?", (dia_selecionado,))
        row = c.fetchone()
        if row:
            agua_atual, meta = row[0], row[1]
        else:
            agua_atual, meta = 0.0, 3.0
        
        agua_meta_input.value = str(meta)
        txt_agua_atual.value = f"{agua_atual:.2f}L"
        barra_agua.value = min(1.0, agua_atual / meta) if meta > 0 else 0

        c.execute("SELECT id, categoria, texto, concluida FROM tarefas WHERE dia=?", (dia_selecionado,))
        tarefas = c.fetchall()

        if tarefas:
            for task_id, cat, txt, concluida in tarefas:
                if cat == "trabalho": criar_tarefa_ui(txt, coluna_trab, checks_trabalho, "#3A86FF", cat, task_id, bool(concluida))
                elif cat == "estudos": criar_tarefa_ui(txt, coluna_estudos, checks_estudos, "#FFBE0B", cat, task_id, bool(concluida))
                elif cat == "casa": criar_tarefa_ui(txt, coluna_casa, checks_casa, "#9CA3AF", cat, task_id, bool(concluida))
                elif cat == "familia": criar_tarefa_ui(txt, coluna_familia, checks_familia, "#F472B6", cat, task_id, bool(concluida))

            # --- RENDERIZAÇÃO DA TABELA DE TREINOS ---
            treinos_do_dia = [t for t in tarefas if t[1] == "treinos"]
            grupos_treino = {}
            
            for task_id, cat, txt, concluida in treinos_do_dia:
                partes = txt.split("|||")
                alarme_salvo = ""
                if len(partes) >= 4:
                    titulo = partes[0]
                    ex = partes[1]
                    reps = partes[2]
                    peso = partes[3]
                    if len(partes) == 5:
                        alarme_salvo = partes[4]
                else:
                    titulo = "Outros"
                    ex = txt
                    reps = ""
                    peso = ""
                
                if titulo not in grupos_treino: 
                    grupos_treino[titulo] = []
                grupos_treino[titulo].append((task_id, ex, reps, peso, alarme_salvo, bool(concluida)))

            for titulo, exs in grupos_treino.items():
                alarme_do_grupo = ""
                for _, _, _, _, alarme, _ in exs:
                    if alarme:
                        alarme_do_grupo = alarme
                        break 
                
                if alarme_do_grupo and titulo != "Outros":
                    conteudo_header = ft.Row([
                        ft.Text(titulo.upper(), weight="bold", size=14, color=ft.Colors.WHITE),
                        ft.Row([
                            ft.Icon(ft.Icons.ALARM, size=14, color="#39FF14"), 
                            ft.Text(alarme_do_grupo, size=12, color="#39FF14", weight="bold")
                        ], spacing=2)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                else:
                    conteudo_header = ft.Container(content=ft.Text(titulo.upper(), weight="bold", size=14, color=ft.Colors.WHITE), alignment=ft.Alignment(0, 0))

                coluna_treinos.controls.append(
                    ft.Container(
                        content=conteudo_header,
                        bgcolor="#374151",
                        padding=ft.padding.symmetric(vertical=4, horizontal=10),
                        border_radius=8,
                        margin=ft.margin.only(top=10, bottom=5)
                    )
                )
                
                if titulo != "Outros":
                    coluna_treinos.controls.append(
                        ft.Row([
                            ft.Container(width=30), 
                            ft.Text("Exercício", size=11, color="#9CA3AF", weight="bold", expand=True),
                            ft.Text("Reps", size=11, color="#9CA3AF", weight="bold", width=45, text_align=ft.TextAlign.CENTER),
                            ft.Text("Peso", size=11, color="#9CA3AF", weight="bold", width=45, text_align=ft.TextAlign.CENTER),
                            ft.Container(width=30) 
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )

                for task_id, ex, reps, peso, _, concluida in exs:
                    chk = ft.Checkbox(value=bool(concluida), fill_color="#39FF14" if concluida else "#FF3D00")
                    checks_treinos.append(chk)
                    chk.on_change = lambda e, tid=task_id, c_obj=chk: on_check_treino(e, tid, c_obj)
                    
                    linha = ft.Row([
                        ft.Container(chk, width=30),
                        ft.Text(ex, size=13, expand=True), 
                        ft.Text(reps if reps else "-", size=12, color="#D1D5DB", width=45, text_align=ft.TextAlign.CENTER),
                        ft.Text(peso if peso else "-", size=12, color="#D1D5DB", width=45, text_align=ft.TextAlign.CENTER),
                        ft.IconButton(icon=ft.Icons.DELETE_ROUNDED, icon_color="#EF4444", icon_size=18, padding=0, width=30, on_click=lambda e, tid=task_id: remover_treino(e, tid))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                    
                    coluna_treinos.controls.append(linha)
        
        atualizar_progresso()

    # --- BARRA DE SEMANA ---
    botoes_dias = []
    def on_click_dia(e, d):
        nonlocal dia_selecionado
        dia_selecionado = d
        for btn in botoes_dias:
            btn.bgcolor = "#00E5FF" if btn.data == dia_selecionado else "#1F2937"
            btn.content.color = "#000000" if btn.data == dia_selecionado else ft.Colors.WHITE
        carregar_dados_do_dia()
        page.update()

    for d in dias_semana:
        btn = ft.Container(
            data=d,
            content=ft.Text(d, weight=ft.FontWeight.BOLD, color="#000000" if d == dia_selecionado else ft.Colors.WHITE, size=12),
            bgcolor="#00E5FF" if d == dia_selecionado else "#1F2937",
            border_radius=8, 
            padding=ft.padding.only(top=6, bottom=6), 
            alignment=ft.Alignment(0, 0),
            on_click=lambda e, dia=d: on_click_dia(e, dia),
            expand=True 
        )
        botoes_dias.append(btn)

    barra_semana = ft.Container(
        content=ft.Row(botoes_dias, spacing=4, alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
        padding=ft.padding.only(left=15, right=15, bottom=10)
    )

    # --- MODO FOCO ---
    txt_timer_foco = ft.Text("00:00", size=70, weight=ft.FontWeight.W_300, color=ft.Colors.WHITE)
    anel_progresso = ft.ProgressRing(value=1.0, stroke_width=6, color="#00E5FF", width=250, height=250)
    
    def fechar_foco(e):
        estado_timer["rodando"] = False
        tela_foco.visible = False
        page.update()

    tela_foco = ft.Container(
        visible=False,
        left=0, top=0, right=0, bottom=0, 
        bgcolor="#F2050A15", 
        content=ft.Column([
            ft.Container(height=100), 
            ft.Stack([
                ft.Container(anel_progresso, alignment=ft.Alignment(0, 0)),
                ft.Container(txt_timer_foco, alignment=ft.Alignment(0, 0)),
            ], width=250, height=250),
            ft.Container(height=40),
            ft.Text("FOCO ATIVO", size=18, color="#9CA3AF", weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            ft.IconButton(ft.Icons.STOP_CIRCLE_OUTLINED, icon_color="#EF4444", on_click=fechar_foco, icon_size=60)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    dropdown_foco = ft.Dropdown(options=[ft.dropdown.Option("1 min"), ft.dropdown.Option("15 min"), ft.dropdown.Option("30 min"), ft.dropdown.Option("45 min"), ft.dropdown.Option("60 min")], width=120, value="30 min", dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)

    def iniciar_timer(e):
        if estado_timer["rodando"]:
            return

        valor = dropdown_foco.value
        try:
            minutos = int(valor.split()[0]) if valor else 30
        except Exception:
            minutos = 30 
            
        estado_timer["segundos"] = minutos * 60
        estado_timer["rodando"] = True
        total_segundos = estado_timer["segundos"]
        
        anel_progresso.color = "#00E5FF"
        anel_progresso.value = 1.0
        txt_timer_foco.value = f"{minutos:02d}:00"
        
        tela_foco.visible = True
        page.update() 
        
        async def contar():
            while estado_timer["rodando"] and estado_timer["segundos"] > 0:
                await asyncio.sleep(1) 
                
                if not estado_timer["rodando"]: 
                    break
                    
                estado_timer["segundos"] -= 1
                m, s = divmod(estado_timer["segundos"], 60)
                
                txt_timer_foco.value = f"{m:02d}:{s:02d}"
                anel_progresso.value = estado_timer["segundos"] / total_segundos
                
                try:
                    txt_timer_foco.update()
                    anel_progresso.update()
                except Exception:
                    pass
                
            if estado_timer["segundos"] <= 0 and estado_timer["rodando"]:
                txt_timer_foco.value = "FEITO!"
                anel_progresso.value = 1.0
                anel_progresso.color = ft.Colors.GREEN_400
                estado_timer["rodando"] = False
                try:
                    txt_timer_foco.update()
                    anel_progresso.update()
                except Exception:
                    pass

        page.run_task(contar)

    # --- MONTAGEM DAS ABAS E TELAS ---
    cartao_foco = criar_cartao("Modo Foco", ft.Row([dropdown_foco, ft.ElevatedButton("Iniciar", on_click=iniciar_timer, bgcolor="#3A86FF", color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Icons.TIMER, "#3A86FF")
    
    aba_saude = ft.ListView(padding=20, controls=[cartao_agua, criar_cartao("Treinos", ft.Column([comp_novo_treino("#FF3D00"), ft.Divider(color="#374151"), coluna_treinos]), ft.Icons.DIRECTIONS_RUN, "#FF3D00")])
    
    aba_trabalho = ft.ListView(padding=20, controls=[cartao_foco, criar_cartao("Trabalho", ft.Column([comp_nova_tarefa(coluna_trab, checks_trabalho, "Tarefas do serviço...", "#3A86FF", "trabalho"), coluna_trab]), ft.Icons.WORK, "#3A86FF"), criar_cartao("Estudos", ft.Column([comp_nova_tarefa(coluna_estudos, checks_estudos, "Ex: Livros, cursos...", "#FFBE0B", "estudos"), coluna_estudos]), ft.Icons.MENU_BOOK, "#FFBE0B")])
    aba_familia = ft.ListView(padding=20, controls=[criar_cartao("Casa", ft.Column([comp_nova_tarefa(coluna_casa, checks_casa, "Tarefas de casa...", "#9CA3AF", "casa"), coluna_casa]), ft.Icons.HOME, "#9CA3AF"), criar_cartao("Família", ft.Column([comp_nova_tarefa(coluna_familia, checks_familia, "Passeios, qualidade...", "#F472B6", "familia"), coluna_familia]), ft.Icons.FAMILY_RESTROOM, "#F472B6")])

    area_conteudo = ft.Container(content=aba_saude, expand=True)

    # --- MENU INFERIOR ---
    def criar_botao_aba(icone, texto, index):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icone, size=14), 
                ft.Text(texto, size=11, weight=ft.FontWeight.BOLD) 
            ], spacing=4, alignment=ft.MainAxisAlignment.CENTER), 
            padding=ft.padding.only(top=12, bottom=12), 
            on_click=lambda e, i=index: mudar_aba(i), 
            ink=True,
            expand=True 
        )

    botoes_abas = [criar_botao_aba(ft.Icons.FAVORITE, "Treinos & Saúde", 0), criar_botao_aba(ft.Icons.WORK, "Trabalhos & Estudos", 1), criar_botao_aba(ft.Icons.HOME, "Casa & Família", 2)]

    def atualizar_botoes(index_ativo):
        for i, btn in enumerate(botoes_abas):
            cor = "#00E5FF" if i == index_ativo else "#9CA3AF"
            borda = "#00E5FF" if i == index_ativo else ft.Colors.TRANSPARENT
            btn.content.controls[0].color = cor
            btn.content.controls[1].color = cor
            btn.border = ft.border.only(bottom=ft.BorderSide(3, borda))
            
    def mudar_aba(index):
        area_conteudo.content = [aba_saude, aba_trabalho, aba_familia][index]
        atualizar_botoes(index)
        page.update()

    atualizar_botoes(0) 
    menu_abas = ft.Container(content=ft.Row(botoes_abas, alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

    carregar_dados_do_dia()

    # --- TELA DE LOGIN/CADASTRO ---
    usuario_logado = False 

    email_input = ft.TextField(
        label="Seu e-mail",
        border_radius=12,
        bgcolor="#1F2937",
        border_color=ft.Colors.TRANSPARENT,
        dense=True,
        text_size=14,
        width=320,
    )
    telefone_input = ft.TextField(
        label="Seu telefone (opcional)",
        border_radius=12,
        bgcolor="#1F2937",
        border_color=ft.Colors.TRANSPARENT,
        dense=True,
        text_size=14,
        width=320,
    )

    def fechar_tela_login(e):
        global usuario_logado
        usuario_logado = True
        tela_abertura.visible = False
        page.update()

    tela_abertura = ft.Container(
        visible=not usuario_logado,
        left=0, top=0, right=0, bottom=0,
        bgcolor="#F2050A15",
        content=ft.Column([
            ft.Container(height=50), 
            
            ft.Icon(ft.Icons.WHATSHOT, color="#FF9800", size=80),
            
            ft.Text("OnePercent", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Text("Sua evolução diária começa aqui.", size=14, color="#9CA3AF"),
            ft.Container(height=40),
            
            email_input,
            ft.Container(height=5),
            telefone_input,
            ft.Container(height=20),
            
            ft.ElevatedButton(
                "Criar Conta Gratuita",
                icon=ft.Icons.PERSON_ADD,
                bgcolor="#00E5FF", 
                color=ft.Colors.BLACK,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=12),
                    padding=ft.padding.symmetric(horizontal=30, vertical=15),
                ),
                width=320,
                on_click=fechar_tela_login, 
            ),
            
            ft.Container(height=10),
            
            ft.TextButton(
                "Já tenho conta. Entrar",
                icon=ft.Icons.LOGIN,
                style=ft.ButtonStyle(color="#00E5FF"),
                width=320,
                on_click=fechar_tela_login,
            ),
            
            ft.Container(height=30),
            
            ft.TextButton(
                "Continuar sem cadastro (modo local)",
                icon=ft.Icons.ARROW_FORWARD,
                style=ft.ButtonStyle(color="#9CA3AF"),
                width=320,
                on_click=fechar_tela_login,
            ),
            
            ft.Container(expand=True), 
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        '"Por isso, não tema, pois estou com você; não tenha medo, pois sou o seu Deus. Eu o fortalecerei e o ajudarei; eu o segurarei com a destra da minha justiça."',
                        size=12, 
                        color="#9CA3AF", 
                        text_align=ft.TextAlign.CENTER, 
                        italic=True
                    ),
                    ft.Text(
                        "Isaías 41:10", 
                        size=12, 
                        weight=ft.FontWeight.BOLD, 
                        color="#FF9800", 
                        text_align=ft.TextAlign.CENTER
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                padding=ft.padding.only(bottom=30, left=30, right=30)
            )
            
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    page.add(ft.Stack([
        ft.Column([cabecalho, barra_semana, menu_abas, area_conteudo], expand=True, spacing=0),
        tela_foco, 
        tela_abertura 
    ], expand=True))

    # --- O MOTOR DO ALARME RODANDO NO FUNDO ---
    alarmes_disparados = set() 

    async def checar_relogio_alarme():
        while True:
            agora = datetime.datetime.now()
            hora_atual_str = f"{agora.hour:02d}:{agora.minute:02d}"
            hoje_str = dias_semana[agora.weekday()]

            c.execute("SELECT id, texto, concluida FROM tarefas WHERE dia=? AND categoria='treinos'", (hoje_str,))
            treinos = c.fetchall()

            treinos_na_hora = set()

            for tid, txt, concluida in treinos:
                if not concluida and tid not in alarmes_disparados:
                    partes = txt.split("|||")
                    if len(partes) == 5:
                        titulo, _, _, _, alarme = partes
                        if alarme == hora_atual_str:
                            treinos_na_hora.add(titulo) 
                            alarmes_disparados.add(tid)

            if treinos_na_hora:
                lista_bonita = "\n".join([f"🔥 Treino: {t.upper()}" for t in treinos_na_hora])
                disparar_alarme_na_tela(lista_bonita)

            await asyncio.sleep(30) 

    page.run_task(checar_relogio_alarme)

# --- INICIALIZAÇÃO LIMPA E SEGURA ---
ft.app(target=main)
