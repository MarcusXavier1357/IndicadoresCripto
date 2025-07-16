import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import io
import plotly.graph_objs as go
import sqlite3
import os
import base64
import nasdaqdatalink
from datetime import datetime, timedelta
import json
import numpy as np
from scipy.stats import linregress
import nolds
from dash import ctx
# Remover importação do custom_style
# from custom_style import custom_css  # Importa o novo design

# Tema escuro do Bootstrap
external_stylesheets = [dbc.themes.DARKLY, '/assets/custom.css']

# CSS customizado para visual moderno
# Remover o dicionário custom_css antigo daqui

DB_FILE = 'crypto_cache.db'

# Função para inicializar o banco de dados
def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Tabela de ativos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ativos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT
        )
    ''')
    # Tabela de cotações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cotacoes (
            ativo_id INTEGER NOT NULL,
            data DATE NOT NULL,
            preco REAL NOT NULL,
            PRIMARY KEY (ativo_id, data),
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        )
    ''')
    conn.commit()
    conn.close()

# Função para carregar dados do banco para DataFrame
def load_data_from_db():
    if not os.path.exists(DB_FILE):
        return None
    conn = sqlite3.connect(DB_FILE)
    query = '''
        SELECT a.codigo, c.data, c.preco 
        FROM cotacoes c
        JOIN ativos a ON c.ativo_id = a.id
        ORDER BY a.codigo, c.data
    '''
    df_db = pd.read_sql_query(query, conn)
    conn.close()
    if df_db.empty:
        return None
    df_db['data'] = pd.to_datetime(df_db['data'])
    df_pivot = df_db.pivot(index='data', columns='codigo', values='preco').reset_index()
    df_pivot.rename(columns={'data': 'Data'}, inplace=True)
    return df_pivot

# Função para obter o id do ativo
def get_ativo_id(codigo):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM ativos WHERE codigo = ?', (codigo,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    return None

# Função para inserir ativo se não existir
def insert_ativo(codigo, nome=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO ativos (codigo, nome) VALUES (?, ?)', (codigo, nome))
    conn.commit()
    conn.close()

# Função para obter última data salva de um ativo
def get_last_update_date(ativo):
    ativo_id = get_ativo_id(ativo)
    if not ativo_id:
        return None
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(data) FROM cotacoes WHERE ativo_id = ?', (ativo_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result[0]:
        return datetime.strptime(result[0], '%Y-%m-%d').date()
    return None

# Função para salvar dados de cripto no banco
def save_crypto_data_to_db(ativo, df_data):
    insert_ativo(ativo)
    ativo_id = get_ativo_id(ativo)
    if not ativo_id:
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    df_clean = df_data.copy()
    df_clean = df_clean.dropna(subset=['Data'])
    df_clean = df_clean.dropna(subset=[ativo])
    data_to_insert = []
    for _, row in df_clean.iterrows():
        try:
            if pd.isna(row['Data']) or pd.isna(row[ativo]):
                continue
            data_str = row['Data'].strftime('%Y-%m-%d')
            preco = float(row[ativo])
            if preco <= 0 or not pd.notnull(preco):
                continue
            data_to_insert.append((ativo_id, data_str, preco))
        except Exception:
            continue
    if data_to_insert:
        cursor.executemany('''
            INSERT OR IGNORE INTO cotacoes (ativo_id, data, preco)
            VALUES (?, ?, ?)
        ''', data_to_insert)
        conn.commit()
    conn.close()

# Inicializar banco e carregar dados ao iniciar o app
init_database()
df_inicial = load_data_from_db()
df_cache = {}
if df_inicial is not None:
    df_cache['cotacoes'] = df_inicial

# Lista de criptos principais (pode ser reduzida para teste)
CRYPTOS = [
    'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'DOGEUSD', 'TONUSD', 'ADAUSD',
    'SHIBUSD', 'AVAXUSD', 'DOTUSD', 'TRXUSD', 'LINKUSD', 'MATICUSD', 'BCHUSD',
    'UNIUSD', 'NEARUSD', 'LTCUSD', 'ICPUSD', 'APTUSD', 'DAIUSD', 'LEOUSD',
    'XLMUSD', 'ETCUSD', 'OKBUSD', 'FILUSD', 'ARBUSD', 'VETUSD', 'MKRUSD',
    'INJUSD', 'GRTUSD', 'XMRUSD', 'TIAUSD', 'SEIUSD'
]

INFLATION_FILE = 'inflation.json'
PERIODS = [10, 8, 5, 3, 2, 1]

# Função para carregar inflação do arquivo
def load_inflation():
    if os.path.exists(INFLATION_FILE):
        with open(INFLATION_FILE, 'r') as f:
            data = json.load(f)
            return {int(k): float(v) for k, v in data.items()}
    return {p: 0.0 for p in PERIODS}

# Função para salvar inflação no arquivo
def save_inflation(inflation_dict):
    with open(INFLATION_FILE, 'w') as f:
        json.dump({str(k): v for k, v in inflation_dict.items()}, f, indent=4)

# Carregar inflação inicial
default_inflation = load_inflation()

default_results = {}

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

def serve_layout():
    sidebar_children = [
        html.Div("Índice Melão", className="sidebar-title"),
        dcc.Upload(
            id="upload-data",
            children=html.Button("Carregar Arquivo", id="btn-load", className="btn btn-primary", style={"width": "100%", 'marginBottom': '18px'}),
            accept=".xlsx",
            style={"width": "100%"}
        ),
        html.Div(id="ativo-dropdown-container"),
        html.Button("Configurar Inflação", id="btn-inflation", className="btn btn-primary"),
        dbc.Modal([
            dbc.ModalHeader("Configurar Taxas de Inflação (%)"),
            dbc.ModalBody([
                html.Div([
                    html.Div([
                        html.Label(f"{p} anos:", className='filter-label', style={'marginRight': '10px'}),
                        dcc.Input(id=f'inflation-input-{p}', type='number', min=0, max=100, step=0.01, className='form-control', style={'width': '80px'}),
                    ], style={'marginBottom': '15px', 'display': 'flex', 'alignItems': 'center'})
                    for p in PERIODS
                ]),
                html.Div(id='inflation-feedback', style={'color': '#00bfae', 'marginTop': '10px'})
            ]),
            dbc.ModalFooter([
                dbc.Button("Salvar", id="btn-save-inflation", color="success", className="me-2"),
                dbc.Button("Cancelar", id="btn-cancel-inflation", color="secondary")
            ])
        ], id='inflation-modal', is_open=False),
        html.Button("Atualizar Criptomoedas", id="btn-crypto", className="btn btn-primary"),
        html.Div(id='crypto-status', style={'color': '#00bfae', 'marginBottom': '10px', 'fontSize': '0.95rem'}),
        html.Button("Calcular Índices", id="btn-calculate", className="btn btn-primary"),
        html.Div(id='calculo-status', style={'color': '#00bfae', 'marginBottom': '10px', 'fontSize': '0.95rem'}),
        html.Button("Exportar Resultados", id="btn-export", className="btn btn-primary"),
        html.Hr(style={'borderColor': '#444', 'width': '100%'}),
        html.Div("Filtros Avançados", style={'marginTop': '20px', 'marginBottom': '10px', 'fontWeight': 'bold'}),
        html.Div([
            html.Div([
                html.Label('Índice Melão:', className='filter-label'),
                dcc.Input(id='filtro-melao-min', type='number', placeholder='Mín', className='form-control'),
                dcc.Input(id='filtro-melao-max', type='number', placeholder='Máx', className='form-control'),
            ], className='d-flex flex-column mb-2'),
            html.Div([
                html.Label('Hurst (DFA):', className='filter-label'),
                dcc.Input(id='filtro-hurst-min', type='number', placeholder='Mín', className='form-control'),
                dcc.Input(id='filtro-hurst-max', type='number', placeholder='Máx', className='form-control'),
            ], className='d-flex flex-column mb-2'),
            html.Div([
                html.Label('Rentabilidade (%):', className='filter-label'),
                dcc.Input(id='filtro-rent-min', type='number', placeholder='Mín', className='form-control'),
                dcc.Input(id='filtro-rent-max', type='number', placeholder='Máx', className='form-control'),
            ], className='d-flex flex-column mb-2'),
            html.Div([
                html.Label('MDD (%):', className='filter-label'),
                dcc.Input(id='filtro-mdd-min', type='number', placeholder='Mín', className='form-control'),
                dcc.Input(id='filtro-mdd-max', type='number', placeholder='Máx', className='form-control'),
            ], className='d-flex flex-column mb-2'),
            html.Div([
                html.Label('Ativo:', className='filter-label'),
                dcc.Input(id='filtro-ativo', type='text', placeholder='Nome do ativo...', className='form-control'),
            ], className='d-flex flex-column mb-2'),
            html.Label('Períodos:', className='filter-label'),
            html.Div([
                dcc.Checklist(
                    id='filtro-periodos',
                    options=[{'label': f'{p}a', 'value': f'{p} anos'} for p in [1,2,3,5,8,10]],
                    value=[f'{p} anos' for p in [1,2,3,5,8,10]],
                    inline=True,
                    inputStyle={'marginRight': '4px'},
                    style={'color': '#fff'}
                )
            ], style={'marginBottom': '10px'}),
            html.Button('Limpar Filtros', id='btn-limpar-filtros', className='btn btn-secondary', style={'marginTop': '10px', 'width': '100%'}),
            html.Div(id='feedback-filtros', style={'color': '#00bfae', 'marginTop': '10px', 'fontSize': '0.95rem'})
        ], className='card p-3'),
        dcc.Loading(id='loading-filtros', type='circle', color='#00bfae', children=[]),
        dcc.Loading(id='loading-calc', type='circle', color='#00bfae', children=[]),
        dcc.Loading(id='loading-crypto', type='circle', color='#00bfae', children=[]),
    ]
    main_children = [
        html.Div("Dashboard do Índice Melão", className='sidebar-title', style={'fontSize': '2.2rem', 'marginBottom': '36px'}),
        html.Div([
            html.Div([
                dcc.Dropdown(
                    id='dropdown-plot-ativo',
                    options=[{'label': a, 'value': a} for a in df_cache['cotacoes'].columns if a != 'Data'] if 'cotacoes' in df_cache else [],
                    placeholder='Selecione o ativo para plotar',
                    className='form-control',
                    style={'width': '300px', 'marginRight': '16px', 'display': 'inline-block'}
                ),
                html.Button('Plotar Ativo', id='btn-plot-ativo', className='btn btn-primary', style={'width': '150px', 'display': 'inline-block'}),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '16px'}),
            html.Div([
                dcc.Graph(id='main-graph', className='dash-graph'),
            ], className='card'),
            html.Div(id='main-table', className='card', style={'marginTop': '40px'})
        ], className='dashboard-section')
    ]
    return html.Div([
        dcc.Store(id='crypto-update-status'),
        dcc.Store(id='inflation-store', data=default_inflation),
        dcc.Store(id='resultados-store', data=default_results),
        html.Div([
            html.Div(sidebar_children, className='sidebar'),
            html.Div(main_children, className='main-content'),
        ], className='app-container'),
        dcc.Download(id="download-resultados")
    ])

app.layout = serve_layout

# Adicionar dcc.Store para resultados calculados
default_results = []

# Filtros na barra lateral
# (Removida a linha: app.layout.children[1].children[0].children.append(...))

# Callback para limpar filtros
def filtro_periodos_default():
    return [f'{p} anos' for p in [1,2,3,5,8,10]]

@app.callback(
    Output('filtro-melao-min', 'value'),
    Output('filtro-melao-max', 'value'),
    Output('filtro-hurst-min', 'value'),
    Output('filtro-hurst-max', 'value'),
    Output('filtro-rent-min', 'value'),
    Output('filtro-rent-max', 'value'),
    Output('filtro-mdd-min', 'value'),
    Output('filtro-mdd-max', 'value'),
    Output('filtro-ativo', 'value'),
    Output('filtro-periodos', 'value'),
    Output('feedback-filtros', 'children'),
    Input('btn-limpar-filtros', 'n_clicks'),
    prevent_initial_call=True
)
def limpar_filtros(n):
    return None, None, None, None, None, None, None, None, '', filtro_periodos_default(), 'Filtros limpos!'

# Adicionar botão Limpar Filtros e tooltips na barra lateral
# (Removida a linha: sidebar = app.layout.children[1].children[0])

# (Removidos os antigos callbacks de main-table.children, calculo-status.children e ativo-dropdown-container)

@app.callback(
    [Output('main-table', 'children'), Output('calculo-status', 'children')],
    [
        Input('upload-data', 'contents'),
        Input('crypto-update-status', 'data'),
        Input('btn-calculate', 'n_clicks'),
        Input('resultados-store', 'data'),
        Input('filtro-melao-min', 'value'),
        Input('filtro-melao-max', 'value'),
        Input('filtro-hurst-min', 'value'),
        Input('filtro-hurst-max', 'value'),
        Input('filtro-rent-min', 'value'),
        Input('filtro-rent-max', 'value'),
        Input('filtro-mdd-min', 'value'),
        Input('filtro-mdd-max', 'value'),
        Input('filtro-ativo', 'value'),
        Input('filtro-periodos', 'value'),
        State('upload-data', 'filename'),
        State('inflation-store', 'data')
    ],
    prevent_initial_call=True
)
def atualizar_tabela_e_status(
    upload_contents, crypto_status, n_clicks_calcular, resultados, melao_min, melao_max, hurst_min, hurst_max, rent_min, rent_max, mdd_min, mdd_max, ativo, periodos, upload_filename, inflation_data
):
    ctx = callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    status = ""
    # Upload de arquivo
    if trigger == 'upload-data':
        if upload_contents is not None and upload_filename and upload_filename.endswith('.xlsx'):
            content_type, content_string = upload_contents.split(',')
            decoded = io.BytesIO(base64.b64decode(content_string))
            try:
                df = pd.read_excel(decoded, parse_dates=[0])
                first_col = df.columns[0]
                df.rename(columns={str(first_col): 'Data'}, inplace=True)
                df_cache['cotacoes'] = df
                ativos = [col for col in df.columns if col != 'Data']
                if ativos:
                    dropdown = dcc.Dropdown(
                        id='ativo-dropdown',
                        options=[{'label': a, 'value': a} for a in ativos],
                        value=ativos[0],
                        placeholder='Selecione um ativo',
                        style={'marginBottom': '18px', 'color': '#23272f'}
                    )
                table = dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in df.columns],
                    data=df.head(30).to_dict('records'),
                    style_table={'overflowX': 'auto', 'background': '#23272f'},
                    style_header={'backgroundColor': '#23272f', 'color': '#fff', 'fontWeight': 'bold'},
                    style_cell={'backgroundColor': '#23272f', 'color': '#fff', 'border': '1px solid #444'},
                    page_size=30
                )
                return table, status
            except Exception as e:
                return html.Div(f"Erro ao ler arquivo: {str(e)}", style={'color': 'red'}), status
        df = df_cache.get('cotacoes')
        if df is not None:
            ativos = [col for col in df.columns if col != 'Data']
            if ativos:
                dropdown = dcc.Dropdown(
                    id='ativo-dropdown',
                    options=[{'label': a, 'value': a} for a in ativos],
                    value=ativos[0],
                    placeholder='Selecione um ativo',
                    style={'marginBottom': '18px', 'color': '#23272f'}
                )
            table = dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.head(30).to_dict('records'),
                style_table={'overflowX': 'auto', 'background': '#23272f'},
                style_header={'backgroundColor': '#23272f', 'color': '#fff', 'fontWeight': 'bold'},
                style_cell={'backgroundColor': '#23272f', 'color': '#fff', 'border': '1px solid #444'},
                page_size=30
            )
            return table, status
        return html.Div("Nenhum arquivo carregado.", style={'color': '#aaa'}), status
    # Atualização de cripto
    elif trigger == 'crypto-update-status':
        if crypto_status and crypto_status.get('updated'):
            df = load_data_from_db()
            df_cache['cotacoes'] = df
            if df is not None:
                ativos = [col for col in df.columns if col != 'Data']
                if ativos:
                    dropdown = dcc.Dropdown(
                        id='ativo-dropdown',
                        options=[{'label': a, 'value': a} for a in ativos],
                        value=ativos[0],
                        placeholder='Selecione um ativo',
                        style={'marginBottom': '18px', 'color': '#23272f'}
                    )
                table = dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in df.columns],
                    data=df.head(30).to_dict('records') if df is not None else [],
                    style_table={'overflowX': 'auto', 'background': '#23272f'},
                    style_header={'backgroundColor': '#23272f', 'color': '#fff', 'fontWeight': 'bold'},
                    style_cell={'backgroundColor': '#23272f', 'color': '#fff', 'border': '1px solid #444'},
                    page_size=30
                )
                return table, status
            else:
                return html.Div("Nenhum dado encontrado.", style={'color': '#aaa'}), status
        return html.Div("Nenhum dado encontrado.", style={'color': '#aaa'}), status
    # Cálculo de índices
    elif trigger == 'btn-calculate':
        df = df_cache.get('cotacoes')
        if df is None:
            return html.Div("Nenhum dado carregado.", style={'color': '#aaa'}), ""
        resultados = calcular_indices(df, inflation_data)
        if not resultados:
            return html.Div("Nenhum resultado encontrado.", style={'color': '#aaa'}), ""
        dash_table_columns = [
            "Ativo", "Período", "Rentabilidade Anual (%)", "MDD (%)", "MDD*", "Índice Melão", "Índice de Sharpe", "Inflação Anual (%)", "Slope", "Hurst (DFA)"
        ]
        table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in dash_table_columns],
            data=[dict(zip(dash_table_columns, row)) for row in resultados],
            style_table={'overflowX': 'auto', 'background': '#23272f'},
            style_header={'backgroundColor': '#23272f', 'color': '#fff', 'fontWeight': 'bold'},
            style_cell={'backgroundColor': '#23272f', 'color': '#fff', 'border': '1px solid #444'},
            page_size=30
        )
        status = f"Cálculo concluído: {len(resultados)} resultados."
        return table, status
    # Filtros
    elif trigger is not None and trigger.startswith('filtro-'):
        if not resultados:
            return html.Div("Nenhum resultado encontrado.", style={'color': '#aaa'}), status
        filtrados = []
        for row in resultados:
            try:
                melao = float(row[5])
                if melao_min is not None and melao < melao_min:
                    continue
                if melao_max is not None and melao > melao_max:
                    continue
                hurst_str = row[9]
                if hurst_str != "N/A":
                    hurst = float(hurst_str)
                    if hurst_min is not None and hurst < hurst_min:
                        continue
                    if hurst_max is not None and hurst > hurst_max:
                        continue
                rent = float(row[2].replace('%', ''))
                if rent_min is not None and rent < rent_min:
                    continue
                if rent_max is not None and rent > rent_max:
                    continue
                mdd = float(row[3].replace('%', ''))
                if mdd_min is not None and mdd < mdd_min:
                    continue
                if mdd_max is not None and mdd > mdd_max:
                    continue
                if ativo:
                    if ativo.lower() not in row[0].lower():
                        continue
                if periodos:
                    if row[1] not in periodos:
                        continue
                filtrados.append(row)
            except Exception:
                continue
        dash_table_columns = [
            "Ativo", "Período", "Rentabilidade Anual (%)", "MDD (%)", "MDD*", "Índice Melão", "Índice de Sharpe", "Inflação Anual (%)", "Slope", "Hurst (DFA)"
        ]
        table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in dash_table_columns],
            data=[dict(zip(dash_table_columns, row)) for row in filtrados],
            style_table={'overflowX': 'auto', 'background': '#23272f'},
            style_header={'backgroundColor': '#23272f', 'color': '#fff', 'fontWeight': 'bold'},
            style_cell={'backgroundColor': '#23272f', 'color': '#fff', 'border': '1px solid #444'},
            page_size=30,
            sort_action='native',
            sort_mode='multi',
        )
        return table, status
    # Default
    return dash.no_update, dash.no_update

# Callback para atualizar criptomoedas
def fetch_crypto_data_incremental(crypto_code):
    # Busca incremental igual ao main.py
    last_date = get_last_update_date(crypto_code)
    if last_date:
        start_date = last_date + timedelta(days=1)
    else:
        start_date = None
    try:
        df_crypto = nasdaqdatalink.get_table(
            'QDL/BITFINEX',
            code=crypto_code,
            paginate=True
        )
        date_column = 'date' if 'date' in df_crypto.columns else 'Date'
        df_crypto = df_crypto[[date_column, 'mid']]
        df_crypto.columns = ['Data', crypto_code]
        df_crypto['Data'] = pd.to_datetime(df_crypto['Data'])
        df_crypto.sort_values('Data', inplace=True)
        if last_date:
            df_crypto = df_crypto[df_crypto['Data'].dt.date > last_date]
        if not df_crypto.empty:
            save_crypto_data_to_db(crypto_code, df_crypto)
        return True, len(df_crypto)
    except Exception as e:
        return False, str(e)

@app.callback(
    Output('crypto-update-status', 'data'),
    Output('crypto-status', 'children'),
    Input('btn-crypto', 'n_clicks'),
    prevent_initial_call=True
)
def atualizar_criptos(n_clicks):
    api_key = os.getenv('apikey')
    if not api_key:
        return dash.no_update, 'API key não encontrada. Configure a variável de ambiente "apikey".'
    nasdaqdatalink.ApiConfig.api_key = api_key # type: ignore
    total = len(CRYPTOS)
    status_msgs = []
    for i, crypto_code in enumerate(CRYPTOS):
        status_msgs.append(f'Atualizando {crypto_code} ({i+1}/{total})...')
        ok, info = fetch_crypto_data_incremental(crypto_code)
        if not ok:
            status_msgs.append(f'Erro em {crypto_code}: {info}')
    status_msgs.append('Atualização concluída!')
    return {'updated': True}, [html.Span(msg) for msg in status_msgs] + [html.Br()]

@app.callback(
    Output('ativo-dropdown-container', 'children'),
    Input('crypto-update-status', 'data'),
    prevent_initial_call=True
)
def atualizar_tabela_apos_cripto(status):
    if status and status.get('updated'):
        df = load_data_from_db()
        df_cache['cotacoes'] = df
        dropdown = None
        if df is not None:
            ativos = [col for col in df.columns if col != 'Data']
            if ativos:
                dropdown = dcc.Dropdown(
                    id='ativo-dropdown',
                    options=[{'label': a, 'value': a} for a in ativos],
                    value=ativos[0],
                    placeholder='Selecione um ativo',
                    style={'marginBottom': '18px', 'color': '#23272f'}
                )
            table = dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.head(30).to_dict('records'),
                style_table={'overflowX': 'auto', 'background': '#23272f'},
                style_header={'backgroundColor': '#23272f', 'color': '#fff', 'fontWeight': 'bold'},
                style_cell={'backgroundColor': '#23272f', 'color': '#fff', 'border': '1px solid #444'},
                page_size=30
            )
            return dropdown
        return html.Div("Nenhum dado encontrado.", style={'color': '#aaa'}), None
    return dash.no_update, dash.no_update

# Callbacks para abrir/fechar modal e preencher inputs
@app.callback(
    Output('inflation-modal', 'is_open'),
    Output('inflation-feedback', 'children'),
    [Input('btn-inflation', 'n_clicks'),
     Input('btn-save-inflation', 'n_clicks'),
     Input('btn-cancel-inflation', 'n_clicks')],
    [State('inflation-modal', 'is_open'),
     State('inflation-store', 'data')] + [State(f'inflation-input-{p}', 'value') for p in PERIODS]
)
def toggle_inflation_modal(btn_open, btn_save, btn_cancel, is_open, inflation_data, *inputs):
    ctx = callback_context
    if not ctx.triggered:
        return is_open, ''
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'btn-inflation':
        return True, ''
    elif trigger == 'btn-cancel-inflation':
        return False, ''
    elif trigger == 'btn-save-inflation':
        # Salvar inflação
        new_inflation = {p: (inputs[i] if inputs[i] is not None else 0.0) for i, p in enumerate(PERIODS)}
        save_inflation(new_inflation)
        return False, 'Inflação salva com sucesso!'
    return is_open, ''

# Callback para preencher os inputs com os valores atuais
@app.callback(
    [Output(f'inflation-input-{p}', 'value') for p in PERIODS],
    Input('inflation-modal', 'is_open'),
    State('inflation-store', 'data')
)
def fill_inflation_inputs(is_open, inflation_data):
    if is_open and inflation_data:
        return [inflation_data.get(p, 0.0) for p in PERIODS]
    return [dash.no_update for _ in PERIODS]

# Callback para atualizar o store após salvar inflação
@app.callback(
    Output('inflation-store', 'data'),
    Input('btn-save-inflation', 'n_clicks'),
    [State(f'inflation-input-{p}', 'value') for p in PERIODS],
    prevent_initial_call=True
)
def update_inflation_store(n_clicks, *inputs):
    if n_clicks:
        new_inflation = {p: (inputs[i] if inputs[i] is not None else 0.0) for i, p in enumerate(PERIODS)}
        return new_inflation
    return dash.no_update

# Funções de cálculo (iguais ao main.py)
def calculate_rentabilidade(df_periodo, ativo, periodo_anos):
    df = df_periodo[['Data', ativo]].dropna(subset=[ativo])
    if len(df) < 2:
        return None
    min_data = df['Data'].min()
    df['Dias'] = (df['Data'] - min_data).dt.days
    x = df['Dias'].values
    y = np.log(df[ativo].values)
    regressao = linregress(x, y)
    rentabilidade_anual = np.exp(regressao.slope*365) - 1  # type: ignore
    return rentabilidade_anual, regressao.slope  # type: ignore

def calculate_hurst_dfa(series):
    if 'nolds' in globals():
        return nolds.dfa(series)
    return np.nan

def calcular_indices(df_cotacoes, inflacao):
    resultados = []
    ativos = df_cotacoes.columns[1:]
    data_final = df_cotacoes['Data'].max()
    for ativo in ativos:
        df_ativo = df_cotacoes[['Data', ativo]].dropna(subset=[ativo])
        if df_ativo.empty:
            continue
        data_mais_recente = df_ativo['Data'].max()
        if data_mais_recente < (data_final - timedelta(days=7)):
            continue
        min_data_ativo = df_ativo['Data'].min()
        for periodo in [10, 8, 5, 3, 2, 1]:
            data_inicio = data_final - timedelta(days=periodo*365)
            if min_data_ativo > data_inicio:
                continue
            df_periodo = df_cotacoes[(df_cotacoes['Data'] >= data_inicio) & (df_cotacoes['Data'] <= data_final)].copy()
            if df_periodo.empty or df_periodo[ativo].isnull().all():
                continue
            df_periodo[ativo] = df_periodo[ativo].ffill().bfill()
            resultado_rent = calculate_rentabilidade(df_periodo, ativo, periodo)
            if resultado_rent is None:
                continue
            rentabilidade_anual, coef_angular = resultado_rent
            df_periodo['Maximo'] = df_periodo[ativo].cummax()
            df_periodo['Drawdown'] = (df_periodo[ativo] / df_periodo['Maximo']) - 1
            mdd_valor = df_periodo['Drawdown'].min()
            mdd_abs = abs(mdd_valor)
            mdd_star = mdd_abs / (1 - mdd_abs)
            infl_acumulada = inflacao.get(periodo, 0.0) / 100.0
            inflacao_anual = ((1 + infl_acumulada) ** (1/periodo)) - 1
            numerador = np.log(1 + rentabilidade_anual) - np.log(1 + inflacao_anual)
            denominador = np.log(1 + mdd_star) / np.sqrt(periodo)
            if denominador == 0:
                indice_melao = 0
            else:
                indice_melao = (numerador / denominador)
            taxa_livre_risco = 0.10
            try:
                prices_sharpe = df_periodo[ativo].values
                if len(prices_sharpe) > 1:
                    log_prices_sharpe = np.log(prices_sharpe)
                    retornos_diarios = np.diff(log_prices_sharpe)
                    media_retorno_diario = np.mean(retornos_diarios)
                    std_retorno_diario = np.std(retornos_diarios)
                    sharpe = ((media_retorno_diario * 252) - taxa_livre_risco) / (std_retorno_diario * np.sqrt(252)) if std_retorno_diario > 0 else 0
                else:
                    sharpe = 0
            except Exception:
                sharpe = 0
            hurst_dfa = np.nan
            try:
                prices = df_periodo[ativo].values
                if len(prices) > 100:
                    log_prices = np.log(prices)
                    returns = np.diff(log_prices)
                    returns = returns[~np.isnan(returns)]
                    returns = returns[np.isfinite(returns)]
                    if len(returns) >= 100:
                        hurst_dfa = calculate_hurst_dfa(returns)
            except Exception:
                pass
            resultados.append([
                ativo,
                f"{periodo} anos",
                f"{rentabilidade_anual*100:.2f}",
                f"{mdd_abs*100:.2f}",
                f"{mdd_star:.4f}",
                f"{indice_melao:.4f}",
                f"{sharpe:.4f}",
                f"{inflacao_anual*100:.2f}",
                f"{coef_angular:.6f}",
                f"{hurst_dfa:.4f}" if not np.isnan(hurst_dfa) else "N/A" # type: ignore
            ])
    return resultados

# Callback para armazenar resultados calculados
def store_resultados(resultados):
    return resultados

@app.callback(
    Output('resultados-store', 'data'),
    Input('btn-calculate', 'n_clicks'),
    State('inflation-store', 'data'),
    prevent_initial_call=True
)
def calcular_indices_store(n_clicks, inflation_data):
    df = df_cache.get('cotacoes')
    if df is None:
        return []
    resultados = calcular_indices(df, inflation_data)
    return resultados

# Callback para exportar resultados
dcc.Download(id="download-resultados")

# Exportação manual para Excel
@app.callback(
    Output("download-resultados", "data"),
    Input("btn-export", "n_clicks"),
    State('main-table', 'children'),
    prevent_initial_call=True
)
def exportar_resultados(n_clicks, table):
    if not table or not hasattr(table, 'props') or 'data' not in table.props:
        return dash.no_update
    df = pd.DataFrame(table.props['data'])
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='xlsxwriter')  # type: ignore
    buffer.seek(0)
    data = base64.b64encode(buffer.read()).decode()
    return dict(content=data, filename="resultados_melao.xlsx", base64=True)

# Feedback visual para upload, cálculo e exportação
@app.callback(
    Output('feedback-filtros', 'children', allow_duplicate=True),
    Input('download-resultados', 'data'),
    prevent_initial_call=True
)
def feedback_exportar(data):
    if data:
        return 'Exportação concluída com sucesso!'
    return dash.no_update

@app.callback(
    Output('main-graph', 'figure'),
    Input('btn-plot-ativo', 'n_clicks'),
    State('dropdown-plot-ativo', 'value'),
    prevent_initial_call=True
)
def plotar_ativo_callback(n_clicks, ativo):
    if not ativo or 'cotacoes' not in df_cache:
        return go.Figure()
    df = df_cache['cotacoes']
    df_ativo = df[['Data', ativo]].dropna(subset=[ativo]).copy()
    if df_ativo.empty:
        return go.Figure()
    fig = go.Figure()
    # Linha do preço
    fig.add_trace(go.Scatter(x=df_ativo['Data'], y=df_ativo[ativo], mode='lines', name='Cotação', line=dict(color='#1f77b4', width=2)))
    # Linha das máximas
    df_ativo['Maximo'] = df_ativo[ativo].cummax()
    fig.add_trace(go.Scatter(x=df_ativo['Data'], y=df_ativo['Maximo'], mode='lines', name='Máximas', line=dict(color='#ff7f0e', dash='dash', width=1.5), opacity=0.7))
    # Área de drawdown
    fig.add_trace(go.Scatter(x=df_ativo['Data'], y=df_ativo[ativo], fill=None, mode='lines', line=dict(color='rgba(0,0,0,0)'), showlegend=False))
    fig.add_trace(go.Scatter(x=df_ativo['Data'], y=df_ativo['Maximo'], fill='tonexty', mode='lines', line=dict(color='rgba(255,0,0,0.2)'), name='Drawdown', opacity=0.3))
    # Regressões lineares de vários períodos
    periodos = [10, 8, 5, 3, 2, 1]
    period_colors = {10: 'red', 8: 'gray', 5: 'purple', 3: 'cyan', 2: 'orange', 1: 'green'}
    max_data = df_ativo['Data'].max()
    for periodo in periodos:
        data_inicio = max_data - pd.Timedelta(days=periodo*365)
        df_periodo = df_ativo[(df_ativo['Data'] >= data_inicio) & (df_ativo['Data'] <= max_data)]
        if len(df_periodo) < 3:
            continue
        df_reg = df_periodo.copy()
        df_reg['Dias'] = (df_reg['Data'] - df_reg['Data'].min()).dt.days
        df_reg['LogPreco'] = np.log(df_reg[ativo])
        try:
            slope, intercept = np.polyfit(df_reg['Dias'], df_reg['LogPreco'], 1)
            df_reg['Regressao'] = np.exp(slope * df_reg['Dias'] + intercept)
            fig.add_trace(go.Scatter(x=df_reg['Data'], y=df_reg['Regressao'], mode='lines',
                                     name=f'Regressão {periodo}a',
                                     line=dict(color=period_colors[periodo], dash='dot', width=2)))
        except Exception:
            continue
    fig.update_layout(
        template='plotly_dark',
        title=f'Evolução do preço de {ativo}',
        xaxis_title='Data',
        yaxis_title='Preço',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='#23272f',
        paper_bgcolor='#23272f',
        font=dict(color='#fff'),
    )
    return fig

if __name__ == "__main__":
    app.run(debug=True) 