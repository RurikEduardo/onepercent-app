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

    # --- GRÁFICO DE RADAR ---
    texto_porcentagem = ft.Text("0%", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    tamanho_radar = 180 
    cx, cy = tamanho_radar / 2, tamanho_radar / 2
    R = tamanho_radar / 2 - 30 

    forma_fundo = cv.Path(
        [
            cv.Path.MoveTo(cx, cy - R), cv.Path.LineTo(cx + R * 0.866, cy - R * 0.5), cv.Path.LineTo(cx + R * 0.866, cy + R * 0.5),
            cv.Path.LineTo(cx, cy + R), cv.Path.LineTo(cx - R * 0.866, cy + R * 0.5), cv.Path.LineTo(cx - R * 0.866, cy - R * 0.5), cv.Path.LineTo(cx, cy - R)
        ], paint=ft.Paint(style=ft.PaintingStyle.STROKE, color=ft.Colors.RED, stroke_width=2)
    )

    forma_dinamica = cv.Path([], paint=ft.Paint(style=ft.PaintingStyle.FILL, color="#99FFFF00"))
    canvas_radar = cv.Canvas([forma_fundo, forma_dinamica], width=tamanho_radar, height=tamanho_radar)

    def atualizar_progresso(e=None):
        def calc_pct(lista):
            return sum(1 for c in lista if c.value) / len(lista) if len(lista) > 0 else 0

        pct_treinos, pct_trab, pct_estudos = calc_pct(checks_treinos), calc_pct(checks_trabalho), calc_pct(checks_estudos)
        pct_casa, pct_familia = calc_pct(checks_casa), calc_pct(checks_familia)
        
        meta_agua = float(agua_meta_input.value.replace(',', '.')) if agua_meta_input.value else 3.0
        pct_agua = min(1.0, agua_atual / meta_agua) if meta_agua > 0 else 0

        r_tre, r_agu, r_tra = R * max(0.05, pct_treinos), R * max(0.05, pct_agua), R * max(0.05, pct_trab)
        r_est, r_cas, r_fam = R * max(0.05, pct_estudos), R * max(0.05, pct_casa), R * max(0.05, pct_familia)
        
        forma_dinamica.elements = [
            cv.Path.MoveTo(cx, cy - r_tre), cv.Path.LineTo(cx + r_agu * 0.866, cy - r_agu * 0.5),
            cv.Path.LineTo(cx + r_tra * 0.866, cy + r_tra * 0.5), cv.Path.LineTo(cx, cy + r_est),
            cv.Path.LineTo(cx - r_cas * 0.866, cy + r_cas * 0.5), cv.Path.LineTo(cx - r_fam * 0.866, cy - r_fam * 0.5), cv.Path.LineTo(cx, cy - r_tre),
        ]

        total_items = len(checks_treinos) + len(checks_trabalho) + len(checks_estudos) + len(checks_casa) + len(checks_familia) + 1 
        concluidas = sum(1 for c in checks_treinos + checks_trabalho + checks_estudos + checks_casa + checks_familia if c.value)
        if pct_agua >= 1.0: concluidas += 1

        geral = (concluidas / total_items) if total_items > 0 else 0
        texto_porcentagem.value = f"{int(geral * 100)}%"
        
        if geral == 1.0:
            if not estado_gamificacao["dias_cumpridos_hoje"]:
                estado_gamificacao["dias_cumpridos_hoje"] = True
                estado_gamificacao["dias_cumpridos_semana"] += 1
                if estado_gamificacao["dias_cumpridos_semana"] >= 5 and estado_gamificacao["nivel"] == 1:
                    estado_gamificacao["nivel"] = 2
                    badges_gamificacao.controls[1].content.controls[1].value = "Nível 2"
                    badges_gamificacao.update()
        page.update()

    bloco_radar = ft.Stack([
        ft.Container(canvas_radar, alignment=ft.Alignment(0, 0)),
        ft.Container(texto_porcentagem, width=tamanho_radar, height=tamanho_radar, alignment=ft.Alignment(0, 0)),
        ft.Container(ft.Text("Treinos", size=10, weight="bold", color="#FF3D00"), top=0, left=cx-18),
        ft.Container(ft.Text("Água", size=10, weight="bold", color="#00E5FF"), top=40, right=0),
        ft.Container(ft.Text("Trab", size=10, weight="bold", color="#3A86FF"), bottom=40, right=0),
        ft.Container(ft.Text("Estudos", size=10, weight="bold", color="#FFBE0B"), bottom=0, left=cx-18),
        ft.Container(ft.Text("Casa", size=10, weight="bold", color="#9CA3AF"), bottom=40, left=0),
        ft.Container(ft.Text("Família", size=10, weight="bold", color="#F472B6"), top=40, left=0),
    ], width=tamanho_radar, height=tamanho_radar)

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

    c.execute("SELECT peso, altura, meta FROM metricas WHERE id=1")
    row_metrics = c.fetchone()
    if row_metrics:
        p_input.value = str(row_metrics[0])
        a_input.value = str(row_metrics[1])
        m_input.value = str(row_metrics[2])
        calc_imc(None)
        calc_meta(None)

    # --- EMBLEMAS E CABEÇALHO ---
    badges_gamificacao = ft.Row([
        ft.Container(content=ft.Row([ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#FFBE0B", size=16), ft.Text("1 Dia", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]), bgcolor="#1F2937", padding=ft.padding.only(left=8, right=8, top=4, bottom=4), border_radius=12),
        ft.Container(content=ft.Row([ft.Icon(ft.Icons.ROCKET_LAUNCH, color="#00E5FF", size=16), ft.Text("Nível 1", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]), bgcolor="#1F2937", padding=ft.padding.only(left=8, right=8, top=4, bottom=4), border_radius=12)
    ])

    arte_cabecalho = cv.Canvas(
        height=250, 
        shapes=[
            cv.Path(elements=[cv.Path.MoveTo(0, 80), cv.Path.CubicTo(100, 10, 200, 150, 420, 60)], paint=ft.Paint(color="#4400E5FF", style=ft.PaintingStyle.STROKE, stroke_width=4)),
            cv.Path(elements=[cv.Path.MoveTo(0, 120), cv.Path.CubicTo(150, 200, 250, 20, 420, 100)], paint=ft.Paint(color="#44FFBE0B", style=ft.PaintingStyle.STROKE, stroke_width=4)),
            cv.Path(elements=[cv.Path.MoveTo(0, 100), cv.Path.CubicTo(120, 120, 300, 60, 420, 140)], paint=ft.Paint(color="#11FFFFFF", style=ft.PaintingStyle.STROKE, stroke_width=2))
        ]
    )

    cabecalho = ft.Stack([
        arte_cabecalho, 
        ft.Container(
            padding=ft.padding.only(top=30, left=20, right=20, bottom=15),
            content=ft.Row([
                ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.PERSON, icon_color=ft.Colors.WHITE, icon_size=20, on_click=abrir_modal_metricas, tooltip="Status do Personagem", padding=0),
                        ft.Text(texto_data, size=14, color="#00E5FF", weight=ft.FontWeight.BOLD)
                    ], alignment=ft.MainAxisAlignment.START, spacing=5), 
                    ft.Text("Evolua 1%", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text("todos os dias!", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(height=2),
                    ft.Text("A constância constrói resultados.", size=12, color="#9CA3AF"),
                    ft.Container(height=8),
                    badges_gamificacao
                ], expand=True),
                bloco_radar
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
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

    # --- TAREFAS DINÂMICAS ---
    coluna_treinos, coluna_trab, coluna_estudos, coluna_casa, coluna_familia = ft.Column(), ft.Column(), ft.Column(), ft.Column(), ft.Column()

    def criar_tarefa_ui(texto, coluna_destino, lista_checks, cor, categoria, task_id=None, concluida=False):
        if task_id is None:
            c.execute("INSERT INTO tarefas (dia, categoria, texto, concluida) VALUES (?, ?, ?, 0)", (dia_selecionado, categoria, texto))
            conn.commit()
            task_id = c.lastrowid

        chk = ft.Checkbox(label=texto, value=concluida, fill_color=cor)
        lista_checks.append(chk)

        def on_check(e):
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

    # --- O NOVO FORMULÁRIO DE TREINOS COM DETALHES AVANÇADOS ---
    def comp_novo_treino(coluna_destino, lista_checks, cor, categoria):
        campo_titulo = ft.TextField(hint_text="Título (Ex: Peito, Corrida)", text_size=14, expand=True, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        campo_exercicio = ft.TextField(hint_text="Exercício (Ex: Supino Reto)", text_size=14, expand=True, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        campo_reps = ft.TextField(hint_text="Reps/Séries (Opcional)", text_size=12, expand=1, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        campo_peso = ft.TextField(hint_text="Peso (Opcional)", text_size=12, expand=1, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        
        def add(e):
            if campo_titulo.value and campo_exercicio.value:
                texto_final = f"[{campo_titulo.value}] {campo_exercicio.value}"
                detalhes = []
                if campo_reps.value: detalhes.append(f"{campo_reps.value}")
                if campo_peso.value: detalhes.append(f"{campo_peso.value}")
                if detalhes: texto_final += f"\n↳ " + " | ".join(detalhes)
                    
                criar_tarefa_ui(texto_final, coluna_destino, lista_checks, cor, categoria)
                
                campo_exercicio.value = ""
                campo_reps.value = ""
                campo_peso.value = ""
                page.update()
                
        return ft.Column([
            campo_titulo,
            campo_exercicio,
            ft.Row([campo_reps, campo_peso, ft.IconButton(icon=ft.Icons.ADD_BOX, icon_color=cor, icon_size=35, on_click=add, padding=ft.padding.only(top=8))])
        ], spacing=5)

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
                if cat == "treinos": criar_tarefa_ui(txt, coluna_treinos, checks_treinos, "#FF3D00", cat, task_id, bool(concluida))
                elif cat == "trabalho": criar_tarefa_ui(txt, coluna_trab, checks_trabalho, "#3A86FF", cat, task_id, bool(concluida))
                elif cat == "estudos": criar_tarefa_ui(txt, coluna_estudos, checks_estudos, "#FFBE0B", cat, task_id, bool(concluida))
                elif cat == "casa": criar_tarefa_ui(txt, coluna_casa, checks_casa, "#9CA3AF", cat, task_id, bool(concluida))
                elif cat == "familia": criar_tarefa_ui(txt, coluna_familia, checks_familia, "#F472B6", cat, task_id, bool(concluida))
        
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
            content=ft.Text(d, weight=ft.FontWeight.BOLD, color="#000000" if d == dia_selecionado else ft.Colors.WHITE),
            bgcolor="#00E5FF" if d == dia_selecionado else "#1F2937",
            border_radius=10, padding=ft.padding.only(left=14, right=14, top=8, bottom=8), alignment=ft.Alignment(0, 0),
            on_click=lambda e, dia=d: on_click_dia(e, dia)
        )
        botoes_dias.append(btn)

    barra_semana = ft.Container(content=ft.Row(botoes_dias, scroll="auto", alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=ft.padding.only(left=20, right=20, bottom=20))

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
    
    aba_saude = ft.ListView(padding=20, controls=[cartao_agua, criar_cartao("Treinos", ft.Column([comp_novo_treino(coluna_treinos, checks_treinos, "#FF3D00", "treinos"), ft.Divider(color="#374151"), coluna_treinos]), ft.Icons.DIRECTIONS_RUN, "#FF3D00")])
    
    aba_trabalho = ft.ListView(padding=20, controls=[cartao_foco, criar_cartao("Trabalho", ft.Column([comp_nova_tarefa(coluna_trab, checks_trabalho, "Tarefas do serviço...", "#3A86FF", "trabalho"), coluna_trab]), ft.Icons.WORK, "#3A86FF"), criar_cartao("Estudos", ft.Column([comp_nova_tarefa(coluna_estudos, checks_estudos, "Ex: Livros, cursos...", "#FFBE0B", "estudos"), coluna_estudos]), ft.Icons.MENU_BOOK, "#FFBE0B")])
    aba_familia = ft.ListView(padding=20, controls=[criar_cartao("Casa", ft.Column([comp_nova_tarefa(coluna_casa, checks_casa, "Tarefas de casa...", "#9CA3AF", "casa"), coluna_casa]), ft.Icons.HOME, "#9CA3AF"), criar_cartao("Família", ft.Column([comp_nova_tarefa(coluna_familia, checks_familia, "Passeios, qualidade...", "#F472B6", "familia"), coluna_familia]), ft.Icons.FAMILY_RESTROOM, "#F472B6")])

    area_conteudo = ft.Container(content=aba_saude, expand=True)

    def criar_botao_aba(icone, texto, index):
        return ft.Container(content=ft.Row([ft.Icon(icone, size=14), ft.Text(texto, size=10, weight=ft.FontWeight.BOLD)]), padding=ft.padding.only(top=10, bottom=10, left=5, right=5), on_click=lambda e, i=index: mudar_aba(i), ink=True)

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
    menu_abas = ft.Container(content=ft.Row(botoes_abas, alignment=ft.MainAxisAlignment.SPACE_EVENLY))

    carregar_dados_do_dia()

    # --- TELA DE LOGIN/CADASTRO COM O VERSÍCULO E AJUSTES ---
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
            # --- AJUSTE DE POSIÇÃO (Conteúdo para cima) ---
            ft.Container(height=50), # Espaço no topo reduzido de 120 para 50
            
            # --- SUBSTITUIÇÃO DO ÍCONE (Foguinho Laranja e Maior) ---
            # ft.Icon(ft.Icons.ROCKET_LAUNCH, color="#00E5FF", size=60), # Antigo
            ft.Icon(ft.Icons.WHATSHOT, color="#FF9800", size=80), # Novo Foguinho Laranja (é um fogo motivacional)
            
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
            
            # --- O VERSÍCULO NO RODAPÉ ---
            ft.Container(expand=True), # Empurra o conteúdo abaixo para o final da tela
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        '"Por isso, não tema, pois estou com você; não tenha medo, pois sou o seu Deus. Eu o fortalecerei e o ajudarei; eu o segurarei com a destra da minha justiça."',
                        size=12, 
                        color="#9CA3AF", 
                        text_align=ft.TextAlign.CENTER, 
                        italic=True
                    ),
                    # --- AJUSTE DE COR (Referência Laranja) ---
                    ft.Text(
                        "Isaías 41:10", 
                        size=12, 
                        weight=ft.FontWeight.BOLD, 
                        # color="#00E5FF", # Antigo Azul Neon
                        color="#FF9800", # Novo Laranja
                        text_align=ft.TextAlign.CENTER
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                padding=ft.padding.only(bottom=30, left=30, right=30)
            )
            
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    page.add(ft.Stack([
        ft.Column([cabecalho, barra_semana, menu_abas, area_conteudo], expand=True),
        tela_foco, 
        tela_abertura 
    ], expand=True))

ft.app(target=main)
