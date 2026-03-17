import flet as ft
import flet.canvas as cv
import time
import threading
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

    # --- INICIALIZAÇÃO SEGURA DO BANCO DE DADOS (MÚLTIPLAS PLATAFORMAS) ---
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

    # --- VARIÁVEIS GLOBAIS E ESTADO ---
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

    # --- GRÁFICO DE RADAR (HEXÁGONO GAMER) ---
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

    # --- MÓDULO DE STATUS DO PERSONAGEM (POP-UP DAS MÉTRICAS) ---
    p_input = ft.TextField(label="Peso (kg)", value="93", expand=1, dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)
    a_input = ft.TextField(label="Alt. (cm)", expand=1, dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)
    res_imc = ft.Text("--", size=20, weight=ft.FontWeight.BOLD, color="#39FF14")
    m_input = ft.TextField(label="Meta (kg)", expand=1, dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)
    res_meta = ft.Text("--", size=20, weight=ft.FontWeight.BOLD, color="#FFBE0B")

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

    def fechar_modal(e):
        modal_metricas.open = False
        page.update()

    def abrir_modal(e):
        modal_metricas.open = True
        page.update()

    modal_metricas = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.Icons.FITNESS_CENTER, color="#39FF14"), ft.Text("Status do Personagem", color=ft.Colors.WHITE, size=18, weight="bold")]),
        content=ft.Container(
            width=300,
            content=ft.Column([
                ft.Text("Atualize suas medidas e metas a qualquer momento. Estes dados ficam salvos no seu sistema.", size=12, color="#9CA3AF"),
                ft.Container(height=10),
                ft.Row([p_input, a_input, ft.IconButton(ft.Icons.CALCULATE, icon_color="#39FF14", on_click=calc_imc), res_imc]),
                ft.Row([m_input, ft.Container(expand=1), ft.IconButton(ft.Icons.TRACK_CHANGES, icon_color="#FFBE0B", on_click=calc_meta), res_meta])
            ], tight=True)
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=fechar_modal, style=ft.ButtonStyle(color="#9CA3AF")),
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

    # --- EMBLEMAS ---
    badges_gamificacao = ft.Row([
        ft.Container(content=ft.Row([ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#FFBE0B", size=16), ft.Text("1 Dia", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]), bgcolor="#1F2937", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=12),
        ft.Container(content=ft.Row([ft.Icon(ft.Icons.ROCKET_LAUNCH, color="#00E5FF", size=16), ft.Text("Nível 1", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)]), bgcolor="#1F2937", padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=12)
    ])

    # --- ARTE DO CABEÇALHO ---
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
                        ft.IconButton(icon=ft.Icons.PERSON, icon_color=ft.Colors.WHITE, icon_size=20, on_click=abrir_modal, tooltip="Status do Personagem", padding=0),
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

    # --- TAREFAS DINÂMICAS (INTEGRADAS COM BANCO DE DADOS) ---
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

        linha = ft.Row([chk, ft.IconButton(icon=ft.Icons.DELETE_ROUNDED, icon_color="#EF4444", icon_size=20, on_click=remover_tarefa)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        coluna_destino.controls.append(linha)
        atualizar_progresso()

    def comp_nova_tarefa(coluna_destino, lista_checks, dica, cor, categoria):
        campo = ft.TextField(hint_text=dica, expand=True, dense=True, bgcolor="#1F2937", border_radius=8, border_color=ft.Colors.TRANSPARENT)
        def add(e):
            if campo.value: criar_tarefa_ui(campo.value, coluna_destino, lista_checks, cor, categoria); campo.value = ""; page.update()
        return ft.Row([campo, ft.IconButton(icon=ft.Icons.ADD_BOX, icon_color=cor, icon_size=35, on_click=add)])

    # --- SISTEMA DE CARREGAMENTO POR DIA ---
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

        if not tarefas:
            pass
        else:
            for task_id, cat, txt, concluida in tarefas:
                if cat == "treinos": criar_tarefa_ui(txt, coluna_treinos, checks_treinos, "#FF3D00", cat, task_id, bool(concluida))
                elif cat == "trabalho": criar_tarefa_ui(txt, coluna_trab, checks_trabalho, "#3A86FF", cat, task_id, bool(concluida))
                elif cat == "estudos": criar_tarefa_ui(txt, coluna_estudos, checks_estudos, "#FFBE0B", cat, task_id, bool(concluida))
                elif cat == "casa": criar_tarefa_ui(txt, coluna_casa, checks_casa, "#9CA3AF", cat, task_id, bool(concluida))
                elif cat == "familia": criar_tarefa_ui(txt, coluna_familia, checks_familia, "#F472B6", cat, task_id, bool(concluida))
        
        atualizar_progresso()

    # --- BARRA DE PLANEJAMENTO SEMANAL CLICÁVEL ---
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
            border_radius=10, padding=ft.padding.symmetric(vertical=8, horizontal=14), alignment=ft.Alignment(0, 0),
            on_click=lambda e, dia=d: on_click_dia(e, dia)
        )
        botoes_dias.append(btn)

    barra_semana = ft.Container(content=ft.Row(botoes_dias, scroll="auto", alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=ft.padding.only(left=20, right=20, bottom=20))

    # --- MODO FOCO (TIMER CORRIGIDO PARA ANDROID) ---
    txt_timer_foco = ft.Text("00:00", size=70, weight=ft.FontWeight.W_300, color=ft.Colors.WHITE)
    anel_progresso = ft.ProgressRing(value=1.0, stroke_width=6, color="#00E5FF", width=250, height=250)
    
    def fechar_foco(e):
        estado_timer["rodando"] = False
        container_foco.visible = False
        page.update()

    container_foco = ft.Container(
        expand=True, bgcolor="black", visible=False,
        content=ft.Column([
            ft.Container(height=120),
            ft.Stack([
                ft.Container(anel_progresso, alignment=ft.Alignment(0, 0)),
                ft.Container(txt_timer_foco, alignment=ft.Alignment(0, 0)),
            ], width=250, height=250),
            ft.Text("FOCO ATIVO", size=16, color="#555555", weight=ft.FontWeight.BOLD),
            ft.IconButton(ft.Icons.STOP_CIRCLE_OUTLINED, icon_color="#333333", on_click=fechar_foco, icon_size=60)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=60)
    )

    dropdown_foco = ft.Dropdown(options=[ft.dropdown.Option("1 min"), ft.dropdown.Option("15 min"), ft.dropdown.Option("30 min"), ft.dropdown.Option("45 min"), ft.dropdown.Option("60 min")], width=120, value="30 min", dense=True, bgcolor="#1F2937", border_color=ft.Colors.TRANSPARENT)

    def iniciar_timer(e):
        minutos = int(dropdown_foco.value.split()[0])
        estado_timer["segundos"] = minutos * 60
        estado_timer["rodando"] = True
        container_foco.visible = True
        anel_progresso.color = "#00E5FF"
        anel_progresso.value = 1.0
        txt_timer_foco.value = f"{minutos:02d}:00"
        page.update()
        
        def contar():
            total = estado_timer["segundos"]
            while estado_timer["segundos"] > 0 and estado_timer["rodando"]:
                m, s = divmod(estado_timer["segundos"], 60)
                txt_timer_foco.value = f"{m:02d}:{s:02d}"
                anel_progresso.value = estado_timer["segundos"] / total
                
                # Atualização forçada para o Android não matar a Thread
                page.update() 
                
                time.sleep(1)
                
                if not estado_timer["rodando"]: break
                estado_timer["segundos"] -= 1
                
            if estado_timer["segundos"] <= 0 and estado_timer["rodando"]:
                txt_timer_foco.value = "FEITO!"
                anel_progresso.color = ft.Colors.GREEN_400
                page.update()
                
        threading.Thread(target=contar, daemon=True).start()

    # --- MONTAGEM DAS ABAS E TELAS ---
    cartao_foco = criar_cartao("Modo Foco", ft.Row([dropdown_foco, ft.ElevatedButton("Iniciar", on_click=iniciar_timer, bgcolor="#3A86FF", color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Icons.TIMER, "#3A86FF")
    
    aba_saude = ft.ListView(padding=20, controls=[cartao_agua, criar_cartao("Treinos", ft.Column([comp_nova_tarefa(coluna_treinos, checks_treinos, "Ex: Corrida...", "#FF3D00", "treinos"), coluna_treinos]), ft.Icons.DIRECTIONS_RUN, "#FF3D00")])
    aba_trabalho = ft.ListView(padding=20, controls=[cartao_foco, criar_cartao("Trabalho", ft.Column([comp_nova_tarefa(coluna_trab, checks_trabalho, "Tarefas do serviço...", "#3A86FF", "trabalho"), coluna_trab]), ft.Icons.WORK, "#3A86FF"), criar_cartao("Estudos", ft.Column([comp_nova_tarefa(coluna_estudos, checks_estudos, "Ex: Livros, cursos...", "#FFBE0B", "estudos"), coluna_estudos]), ft.Icons.MENU_BOOK, "#FFBE0B")])
    aba_familia = ft.ListView(padding=20, controls=[criar_cartao("Casa", ft.Column([comp_nova_tarefa(coluna_casa, checks_casa, "Tarefas de casa...", "#9CA3AF", "casa"), coluna_casa]), ft.Icons.HOME, "#9CA3AF"), criar_cartao("Família", ft.Column([comp_nova_tarefa(coluna_familia, checks_familia, "Passeios, qualidade...", "#F472B6", "familia"), coluna_familia]), ft.Icons.FAMILY_RESTROOM, "#F472B6")])

    area_conteudo = ft.Container(content=aba_saude, expand=True)

    def criar_botao_aba(icone, texto, index):
        return ft.Container(content=ft.Row([ft.Icon(icone, size=14), ft.Text(texto, size=10, weight=ft.FontWeight.BOLD)]), padding=ft.padding.symmetric(vertical=10, horizontal=5), on_click=lambda e, i=index: mudar_aba(i), ink=True)

    botoes_abas = [criar_botao_aba(ft.Icons.FAVORITE, "Treinos & Saúde", 0), criar_botao_aba(ft.Icons.WORK, "Trabalhos & Estudos", 1), criar_botao_aba(ft.Icons.HOME, "Casa & Família", 2)]

    def atualizar_botoes(index_ativo):
        for i, btn in enumerate(botoes_abas):
            cor = "#00E5FF" if i == index_ativo else "#9CA3AF"
            borda = "#00E5FF" if i == index_ativo else ft.Colors.TRANSPARENT
            btn.content.controls[0].color = cor
            btn.content.controls[1].color = cor
            btn.border = ft.border.only(bottom=ft.border.BorderSide(3, borda))
            
    def mudar_aba(index):
        area_conteudo.content = [aba_saude, aba_trabalho, aba_familia][index]
        atualizar_botoes(index)
        page.update()

    atualizar_botoes(0) 
    menu_abas = ft.Container(content=ft.Row(botoes_abas, alignment=ft.MainAxisAlignment.SPACE_EVENLY))

    carregar_dados_do_dia()

    page.add(ft.Stack([
        ft.Column([cabecalho, barra_semana, menu_abas, area_conteudo], expand=True)
    ], expand=True))

ft.app(target=main)
