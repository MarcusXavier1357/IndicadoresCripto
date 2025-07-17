import customtkinter as ctk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import json
from scipy.stats import linregress
from scipy.special import gamma
import nolds
import nasdaqdatalink
from dotenv import load_dotenv
import os
import sqlite3

# Carregar variáveis do .env
load_dotenv()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#333", foreground="white", relief="solid", borderwidth=1, font=("Arial", 9))
        label.pack(ipadx=4, ipady=2)

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class MelaoIndexApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Cálculo do Índice Melão")
        self.geometry("1200x700")
        self.df_cotacoes = None
        self.inflacao = {10: 0.0, 8: 0.0, 5: 0.0, 3: 0.0, 2: 0.0, 1: 0.0}
        self.json_file = "inflation.json"
        self.current_results = []
        self.inflation_window = None
        self.crypto_window = None
        self.after_ids = []
        self.progress_bar = None 
        self.period_vars = {
            10: ctk.BooleanVar(value=True),
            8: ctk.BooleanVar(value=True),
            5: ctk.BooleanVar(value=True),
            3: ctk.BooleanVar(value=True),
            2: ctk.BooleanVar(value=True),
            1: ctk.BooleanVar(value=True)
        }
        api_key = os.getenv('apikey')
        if api_key:
            nasdaqdatalink.ApiConfig.api_key = api_key  # type: ignore
        self.predefined_cryptos = ['BTCUSD', 'ETHUSD', 'XRPUSD', 'LTCUSD', 'ZRXUSD', 'SOLUSD', 'ADAUSD', 'DOTUSD']

        # Inicializar banco de dados
        self.db_file = "crypto_cache.db"
        self.init_database()

        self.create_widgets()
        self.load_inflation()
        
        # Carregar dados salvos automaticamente
        self.load_cached_data()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_close(self):
        """Fechamento seguro da aplicação"""
        for id in self.after_ids:
            self.after_cancel(id)
        
        if self.inflation_window and self.inflation_window.winfo_exists():
            self.inflation_window.destroy()
        
        if self.crypto_window and self.crypto_window.winfo_exists():
            self.crypto_window.destroy()
            
        self.destroy()
        self.quit()
    
    def init_database(self):
        """Inicializa o banco de dados SQLite"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Criar tabela de ativos com IDs fixos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ativos (
                    id INTEGER PRIMARY KEY,
                    codigo TEXT UNIQUE NOT NULL,
                    nome TEXT
                )
            ''')
            
            # Criar tabela de cotações (usando ID do ativo)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cotacoes (
                    ativo_id INTEGER NOT NULL,
                    data DATE NOT NULL,
                    preco REAL NOT NULL,
                    PRIMARY KEY (ativo_id, data),
                    FOREIGN KEY (ativo_id) REFERENCES ativos(id)
                )
            ''')
            
            # Criar tabela de metadados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadados (
                    chave TEXT PRIMARY KEY,
                    valor TEXT
                )
            ''')
            
            # Inserir ativos com IDs fixos (lista limpa - apenas criptomoedas reais)
            ativos_data = [
                (1, '1INCHUSD', '1inch'),
                (2, 'AAVEUSD', 'Aave'),
                (3, 'ABSUSD', 'Absorber'),
                (4, 'AGIUSD', 'SingularityNET'),
                (5, 'AIDUSD', 'AidCoin'),
                (6, 'AIOUSD', 'AIOZ Network'),
                (7, 'AIXUSD', 'Aigang'),
                (8, 'ALBTUSD', 'AllianceBlock'),
                (9, 'ALGUSD', 'Algorand'),
                (10, 'ALT2612USD', 'Altcoin'),
                (11, 'AMPUSD', 'Amp'),
                (12, 'ANCUSD', 'Anchor Protocol'),
                (13, 'ANTUSD', 'Aragon'),
                (14, 'APENFTUSD', 'APENFT'),
                (15, 'APEUSD', 'ApeCoin'),
                (16, 'APPUSD', 'AppCoins'),
                (17, 'APTUSD', 'Aptos'),
                (18, 'ARBUSD', 'Arbitrum'),
                (19, 'ASTUSD', 'AirSwap'),
                (20, 'ATLASUSD', 'Star Atlas'),
                (21, 'ATMUSD', 'Atletico Madrid Fan Token'),
                (22, 'ATOUSD', 'ATO'),
                (23, 'AUCUSD', 'Auctus'),
                (24, 'AUSDTUSD', 'AUSDT'),
                (25, 'AVAXUSD', 'Avalanche'),
                (26, 'AVTUSD', 'Aventus'),
                (27, 'AXSUSD', 'Axie Infinity'),
                (28, 'AZEROUSD', 'Aleph Zero'),
                (29, 'B21XUSD', 'B21'),
                (30, 'B2MUSD', 'Bit2Me'),
                (31, 'BABUSD', 'BAB'),
                (32, 'BALUSD', 'Balancer'),
                (33, 'BANDUSD', 'Band Protocol'),
                (34, 'BATUSD', 'Basic Attention Token'),
                (35, 'BBNUSD', 'BBN'),
                (36, 'BCCUSD', 'BitConnect'),
                (37, 'BCHABCUSD', 'Bitcoin Cash ABC'),
                (38, 'BCHNUSD', 'Bitcoin Cash Node'),
                (39, 'BCHUSD', 'Bitcoin Cash'),
                (40, 'BCIUSD', 'BCI'),
                (41, 'BCUUSD', 'BCU'),
                (42, 'BESTUSD', 'Bitpanda Ecosystem Token'),
                (43, 'BFTUSD', 'BnkToTheFuture'),
                (44, 'BFXUSD', 'BFX'),
                (45, 'BG1USD', 'BG1'),
                (46, 'BG2USD', 'BG2'),
                (47, 'BGBUSD', 'Bitget Token'),
                (48, 'BLURUSD', 'Blur'),
                (49, 'BMIUSD', 'Bridge Mutual'),
                (50, 'BMNUSD', 'BMN'),
                (51, 'BNTUSD', 'Bancor'),
                (52, 'BOBAUSD', 'Boba Network'),
                (53, 'BONKUSD', 'Bonk'),
                (54, 'BOOUSD', 'SpookySwap'),
                (55, 'BORGUSD', 'Borg'),
                (56, 'BOSONUSD', 'Boson Protocol'),
                (57, 'BOXUSD', 'BOX'),
                (58, 'BRISEUSD', 'Bitgert'),
                (59, 'BSVUSD', 'Bitcoin SV'),
                (60, 'BT1USD', 'BT1'),
                (61, 'BT2USD', 'BT2'),
                (62, 'BTCUSD', 'Bitcoin'),
                (63, 'BTGUSD', 'Bitcoin Gold'),
                (64, 'BTSEUSD', 'BTSE Token'),
                (65, 'BTTUSD', 'BitTorrent'),
                (66, 'CBTUSD', 'CommerceBlock'),
                (67, 'CCDUSD', 'Concordium'),
                (68, 'CELOUSD', 'Celo'),
                (69, 'CELUSD', 'Celsius'),
                (70, 'CFIUSD', 'Cofound.it'),
                (71, 'CHEXUSD', 'CHEX'),
                (72, 'CHSBUSD', 'SwissBorg'),
                (73, 'CHZUSD', 'Chiliz'),
                (74, 'CLOUSD', 'Callisto Network'),
                (75, 'CNDUSD', 'Cindicator'),
                (76, 'CNNUSD', 'CNN'),
                (77, 'COMPUSD', 'Compound'),
                (78, 'CONVUSD', 'Convergence'),
                (79, 'CRVUSD', 'Curve DAO Token'),
                (80, 'CSTBCHABCUSD', 'CST BCH ABC'),
                (81, 'CSTBCHNUSD', 'CST BCH Node'),
                (82, 'CSXUSD', 'CSX'),
                (83, 'CTKUSD', 'CertiK'),
                (84, 'CTXUSD', 'Cryptex'),
                (85, 'DADUSD', 'DAD'),
                (86, 'DAIUSD', 'Dai'),
                (87, 'DAPPUSD', 'Dapp.com'),
                (88, 'DATUSD', 'Datum'),
                (89, 'DCRUSD', 'Decred'),
                (90, 'DGBUSD', 'DigiByte'),
                (91, 'DGXUSD', 'Digix Gold'),
                (92, 'DOGEUSD', 'Dogecoin'),
                (93, 'DOGUSD', 'DOG'),
                (94, 'DORAUSD', 'Dora Factory'),
                (95, 'DOTUSD', 'Polkadot'),
                (96, 'DRKUSD', 'DRK'),
                (97, 'DRNUSD', 'DRN'),
                (98, 'DSHUSD', 'Dash'),
                (99, 'DTAUSD', 'Data'),
                (100, 'DTHUSD', 'DTH'),
                (101, 'DTXUSD', 'DTX'),
                (102, 'DUSKUSD', 'Dusk Network'),
                (103, 'DVFUSD', 'DeversiFi'),
                (104, 'DYMUSD', 'Dymension'),
                (105, 'EDOUSD', 'Eidoo'),
                (106, 'EGLDUSD', 'MultiversX'),
                (107, 'ELFUSD', 'aelf'),
                (108, 'ENJUSD', 'Enjin Coin'),
                (109, 'EOSDTUSD', 'EOSDT'),
                (110, 'EOSUSD', 'EOS'),
                (111, 'ESSUSD', 'Essentia'),
                (112, 'ETCUSD', 'Ethereum Classic'),
                (113, 'ETH2XUSD', 'ETH 2x Flexible Leverage Index'),
                (114, 'ETHUSD', 'Ethereum'),
                (115, 'ETHWUSD', 'EthereumPoW'),
                (116, 'ETPUSD', 'Metaverse ETP'),
                (117, 'EUSUSD', 'EUS'),
                (118, 'EUTUSD', 'EUT USD'),
                (119, 'EVTUSD', 'Everitoken'),
                (120, 'EXOUSD', 'Exosis'),
                (121, 'EXRDUSD', 'e-Radix'),
                (122, 'FBTUSD', 'FBT'),
                (123, 'FCLUSD', 'Fractal'),
                (124, 'FETUSD', 'Fetch.ai'),
                (125, 'FILUSD', 'Filecoin'),
                (126, 'FLOKIUSD', 'FLOKI'),
                (127, 'FLRUSD', 'Flare'),
                (128, 'FOAUSD', 'FOA'),
                (129, 'FORTHUSD', 'Ampleforth Governance Token'),
                (130, 'FSNUSD', 'Fusion'),
                (131, 'FTMUSD', 'Fantom'),
                (132, 'FTTUSD', 'FTX Token'),
                (133, 'FUNUSD', 'FunFair'),
                (134, 'GALAUSD', 'Gala'),
                (135, 'GENUSD', 'DAOstack'),
                (136, 'GMMTUSD', 'GMMT'),
                (137, 'GMTUSD', 'STEPN'),
                (138, 'GNOUSD', 'Gnosis'),
                (139, 'GNTUSD', 'Golem'),
                (140, 'GOCUSD', 'GOC'),
                (141, 'GOMININGUSD', 'GoMining'),
                (142, 'GOTUSD', 'GOT'),
                (143, 'GPTUSD', 'GPT'),
                (144, 'GRTUSD', 'The Graph'),
                (145, 'GSDUSD', 'GSD'),
                (146, 'GSTUSD', 'GST'),
                (147, 'GTXUSD', 'GTX'),
                (148, 'GXTUSD', 'GXT'),
                (149, 'HECUSD', 'HEC'),
                (150, 'HEZUSD', 'Hermez Network'),
                (151, 'HILSVUSD', 'HILS'),
                (152, 'HIXUSD', 'HIX'),
                (153, 'HMTUSD', 'Human Protocol'),
                (154, 'HOTUSD', 'Holo'),
                (155, 'HTXUSD', 'HTX'),
                (156, 'ICEUSD', 'ICE'),
                (157, 'ICPUSD', 'Internet Computer'),
                (158, 'IDXUSD', 'IDX'),
                (159, 'IMPUSD', 'Imperium'),
                (160, 'INJUSD', 'Injective'),
                (161, 'INTUSD', 'Internet Node Token'),
                (162, 'IOSUSD', 'IOS'),
                (163, 'IOTUSD', 'IOTA'),
                (164, 'IQXUSD', 'IQX'),
                (165, 'JASMYUSD', 'JasmyCoin'),
                (166, 'JSTUSD', 'JUST'),
                (167, 'JUPUSD', 'Jupiter'),
                (168, 'KAIUSD', 'KardiaChain'),
                (169, 'KANUSD', 'BitKan'),
                (170, 'KARATEUSD', 'Karate Combat'),
                (171, 'KAVAUSD', 'Kava'),
                (172, 'KNCUSD', 'Kyber Network Crystal'),
                (173, 'KSMUSD', 'Kusama'),
                (174, 'LAIUSD', 'LAI'),
                (175, 'LDOUSD', 'Lido DAO'),
                (176, 'LEOUSD', 'LEO Token'),
                (177, 'LIFIIIUSD', 'LIF III'),
                (178, 'LINKUSD', 'Chainlink'),
                (179, 'LOOUSD', 'LOO'),
                (180, 'LRCUSD', 'Loopring'),
                (181, 'LTCUSD', 'Litecoin'),
                (182, 'LUNA2USD', 'Terra 2.0'),
                (183, 'LUNAUSD', 'Terra'),
                (184, 'LUXOUSD', 'LUXO'),
                (185, 'LYMUSD', 'Lympo'),
                (186, 'MANUSD', 'MAN'),
                (187, 'MATICUSD', 'Polygon'),
                (188, 'MEMEUSD', 'MEME'),
                (189, 'MGOUSD', 'MGO'),
                (190, 'MIMUSD', 'Magic Internet Money'),
                (191, 'MIRUSD', 'Mirror Protocol'),
                (192, 'MITUSD', 'MIT'),
                (193, 'MKRUSD', 'Maker'),
                (194, 'MLNUSD', 'Enzyme'),
                (195, 'MNAUSD', 'MNA'),
                (196, 'MOBUSD', 'MobileCoin'),
                (197, 'MTNUSD', 'MTN'),
                (198, 'MXNTUSD', 'MXNT'),
                (199, 'NCAUSD', 'NCA'),
                (200, 'NEARUSD', 'NEAR Protocol'),
                (201, 'NECUSD', 'Nectar'),
                (202, 'NEOUSD', 'NEO'),
                (203, 'NEXOUSD', 'NEXO'),
                (204, 'NIOUSD', 'NIO'),
                (205, 'NOMUSD', 'NOM'),
                (206, 'NUTUSD', 'NUT'),
                (207, 'NXRAUSD', 'NXRA'),
                (208, 'OCEANUSD', 'Ocean Protocol'),
                (209, 'ODEUSD', 'ODE'),
                (210, 'OGNUSD', 'Origin Protocol'),
                (211, 'OKBUSD', 'OKB'),
                (212, 'OMGUSD', 'OMG Network'),
                (213, 'OMNUSD', 'OMN'),
                (214, 'ONEUSD', 'Harmony'),
                (215, 'ONLUSD', 'ONL'),
                (216, 'ONUSUSD', 'ONUS'),
                (217, 'OPXUSD', 'OPX'),
                (218, 'ORSUSD', 'ORS'),
                (219, 'OXYUSD', 'Oxygen'),
                (220, 'PAIUSD', 'PCHAIN'),
                (221, 'PASUSD', 'PAS'),
                (222, 'PAXUSD', 'Paxos Standard'),
                (223, 'PEPEUSD', 'Pepe'),
                (224, 'PLANETSUSD', 'PlanetWatch'),
                (225, 'PLUUSD', 'Pluton'),
                (226, 'PNGUSD', 'Pangolin'),
                (227, 'PNKUSD', 'Kleros'),
                (228, 'POAUSD', 'POA Network'),
                (229, 'POLCUSD', 'PolkaCity'),
                (230, 'POLISUSD', 'Polis'),
                (231, 'POYUSD', 'POY'),
                (232, 'PRMXUSD', 'PRMX'),
                (233, 'QRDOUSD', 'Qredo'),
                (234, 'QSHUSD', 'QASH'),
                (235, 'QTFUSD', 'QTF'),
                (236, 'QTMUSD', 'QTM'),
                (237, 'RBTUSD', 'RBT'),
                (238, 'RCNUSD', 'Ripio Credit Network'),
                (239, 'RDNUSD', 'Raiden Network Token'),
                (240, 'REEFUSD', 'Reef'),
                (241, 'REPUSD', 'Augur'),
                (242, 'REQUSD', 'Request'),
                (243, 'RIFUSD', 'RSK Infrastructure Framework'),
                (244, 'RINGXUSD', 'RINGX'),
                (245, 'RLCUSD', 'iExec RLC'),
                (246, 'RLYUSD', 'Rally'),
                (247, 'ROSEUSD', 'Oasis Network'),
                (248, 'RRBUSD', 'RRB'),
                (249, 'RRTUSD', 'RRT'),
                (250, 'RTEUSD', 'RTE'),
                (251, 'SANDUSD', 'The Sandbox'),
                (252, 'SANUSD', 'Santiment Network Token'),
                (253, 'SCRUSD', 'SCR'),
                (254, 'SEEUSD', 'SEE'),
                (255, 'SEIUSD', 'Sei'),
                (256, 'SENATEUSD', 'SENATE'),
                (257, 'SENUSD', 'SEN'),
                (258, 'SGBUSD', 'SGB'),
                (259, 'SHFTUSD', 'SHFT'),
                (260, 'SHIBUSD', 'Shiba Inu'),
                (261, 'SIDUSUSD', 'SIDUS'),
                (262, 'SMRUSD', 'SMR'),
                (263, 'SNGUSD', 'SNG'),
                (264, 'SNTUSD', 'Status'),
                (265, 'SNXUSD', 'Synthetix'),
                (266, 'SOLUSD', 'Solana'),
                (267, 'SPELLUSD', 'Spell Token'),
                (268, 'SPKUSD', 'SPK'),
                (269, 'SRMUSD', 'Serum'),
                (270, 'STGUSD', 'Stargate Finance'),
                (271, 'STJUSD', 'STJ'),
                (272, 'STRKUSD', 'Strike'),
                (273, 'SUIUSD', 'Sui'),
                (274, 'SUKUUSD', 'SUKU'),
                (275, 'SUNUSD', 'SUN'),
                (276, 'SUSHIUSD', 'SushiSwap'),
                (277, 'SWEATUSD', 'Sweat Economy'),
                (278, 'SWMUSD', 'SWM'),
                (279, 'SXXUSD', 'SXX'),
                (280, 'TENETUSD', 'TENET'),
                (281, 'TERRAUSTUSD', 'TerraUSD'),
                (282, 'THETAUSD', 'Theta Network'),
                (283, 'TIAUSD', 'Celestia'),
                (284, 'TKNUSD', 'Monolith'),
                (285, 'TLOSUSD', 'Telos'),
                (286, 'TNBUSD', 'TNB'),
                (287, 'TOMIUSD', 'TOMI'),
                (288, 'TONUSD', 'Toncoin'),
                (289, 'TRADEUSD', 'TRADE'),
                (290, 'TREEBUSD', 'TREEB'),
                (291, 'TRIUSD', 'TRI'),
                (292, 'TRXUSD', 'TRON'),
                (293, 'TSDUSD', 'TSD'),
                (294, 'TURBOUSD', 'TURBO'),
                (295, 'UDCUSD', 'UDC'),
                (296, 'UFRUSD', 'UFR'),
                (297, 'UNIUSD', 'Uniswap'),
                (298, 'UOPUSD', 'UOP'),
                (299, 'UOSUSD', 'Ultra'),
                (300, 'USKUSD', 'USK'),
                (301, 'USTUSD', 'TerraUSD'),
                (302, 'UTKUSD', 'Utrust'),
                (303, 'UTNUSD', 'UTN'),
                (304, 'VEEUSD', 'BLOCKv'),
                (305, 'VELOUSD', 'VELO'),
                (306, 'VENUSD', 'VeChain'),
                (307, 'VETUSD', 'VeChain'),
                (308, 'VLDUSD', 'VLD'),
                (309, 'VRAUSD', 'Verasity'),
                (310, 'VSYUSD', 'VSY'),
                (311, 'WAVESUSD', 'Waves'),
                (312, 'WAXUSD', 'WAX'),
                (313, 'WBTUSD', 'WBT'),
                (314, 'WHBTUSD', 'WHBT'),
                (315, 'WIFUSD', 'dogwifhat'),
                (316, 'WILDUSD', 'WILD'),
                (317, 'WLOUSD', 'WLO'),
                (318, 'WMINIMAUSD', 'WMINIMA'),
                (319, 'WNCGUSD', 'Wrapped NCG'),
                (320, 'WOOUSD', 'WOO Network'),
                (321, 'WPRUSD', 'WePower'),
                (322, 'WTCUSD', 'Waltonchain'),
                (323, 'XAUTUSD', 'Tether Gold'),
                (324, 'XCADUSD', 'XCAD Network'),
                (325, 'XCHUSD', 'Chia'),
                (326, 'XCNUSD', 'XCN'),
                (327, 'XDCUSD', 'XDC Network'),
                (328, 'XLMUSD', 'Stellar'),
                (329, 'XMRUSD', 'Monero'),
                (330, 'XRAUSD', 'XRA'),
                (331, 'XRDUSD', 'Radix'),
                (332, 'XRPUSD', 'XRP'),
                (333, 'XSNUSD', 'Stakenet'),
                (334, 'XTPUSD', 'XTP'),
                (335, 'XTZUSD', 'Tezos'),
                (336, 'XVGUSD', 'Verge'),
                (337, 'YFIUSD', 'yearn.finance'),
                (338, 'YGGUSD', 'Yield Guild Games'),
                (339, 'YYWUSD', 'YYW'),
                (340, 'ZBTUSD', 'ZBT'),
                (341, 'ZCNUSD', '0chain'),
                (342, 'ZECUSD', 'Zcash'),
                (343, 'ZETAUSD', 'ZetaChain'),
                (344, 'ZILUSD', 'Zilliqa'),
                (345, 'ZMTUSD', 'ZMT'),
                (346, 'ZRXUSD', '0x')
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO ativos (id, codigo, nome)
                VALUES (?, ?, ?)
            ''', ativos_data)
            
            conn.commit()
            conn.close()
            print("Banco de dados inicializado com sucesso!")
            
        except Exception as e:
            print(f"Erro ao inicializar banco de dados: {str(e)}")
    
    def get_ativo_id(self, codigo):
        """Obtém o ID de um ativo pelo código"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM ativos WHERE codigo = ?', (codigo,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            return None
            
        except Exception as e:
            print(f"Erro ao obter ID do ativo {codigo}: {str(e)}")
            return None
    
    def get_last_update_date(self, ativo):
        """Obtém a data da última atualização para um ativo"""
        try:
            ativo_id = self.get_ativo_id(ativo)
            if not ativo_id:
                return None
                
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(data) FROM cotacoes WHERE ativo_id = ?
            ''', (ativo_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return datetime.strptime(result[0], '%Y-%m-%d').date()
            return None
            
        except Exception as e:
            print(f"Erro ao obter última data: {str(e)}")
            return None
    
    def save_crypto_data_to_db(self, ativo, df_data):
        """Salva dados de criptomoeda no banco de dados"""
        try:
            ativo_id = self.get_ativo_id(ativo)
            if not ativo_id:
                print(f"Ativo {ativo} não encontrado na tabela de ativos")
                return
                
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Limpar dados inválidos antes de salvar
            df_clean = df_data.copy()
            
            # Remover linhas com datas inválidas (NaT)
            df_clean = df_clean.dropna(subset=['Data'])
            
            # Remover linhas com preços inválidos (NaN)
            df_clean = df_clean.dropna(subset=[ativo])
            
            # Preparar dados para inserção
            data_to_insert = []
            for _, row in df_clean.iterrows():
                try:
                    # Verificar se os dados são válidos
                    if pd.isna(row['Data']) or pd.isna(row[ativo]):
                        continue
                    
                    # Converter para tipos corretos
                    data_str = row['Data'].strftime('%Y-%m-%d')
                    preco = float(row[ativo])
                    
                    # Verificar se o preço é válido
                    if preco <= 0 or not np.isfinite(preco):
                        continue
                    
                    data_to_insert.append((ativo_id, data_str, preco))
                    
                except (ValueError, TypeError, AttributeError) as e:
                    # Pular linhas com dados inválidos
                    continue
            
            # Inserir dados (ignorar duplicatas)
            if data_to_insert:
                cursor.executemany('''
                    INSERT OR IGNORE INTO cotacoes (ativo_id, data, preco)
                    VALUES (?, ?, ?)
                ''', data_to_insert)
                
                conn.commit()
                print(f"Dados salvos para {ativo} (ID: {ativo_id}): {len(data_to_insert)} registros válidos")
            else:
                print(f"Nenhum dado válido encontrado para {ativo}")
            
            conn.close()
            
        except Exception as e:
            print(f"Erro ao salvar dados no banco: {str(e)}")
            if 'conn' in locals():
                conn.close()
    
    def load_cached_data(self):
        """Carrega dados salvos do banco de dados"""
        try:
            conn = sqlite3.connect(self.db_file)
            
            # Buscar todos os dados salvos com JOIN para obter códigos dos ativos
            query = '''
                SELECT a.codigo, c.data, c.preco 
                FROM cotacoes c
                JOIN ativos a ON c.ativo_id = a.id
                ORDER BY a.codigo, c.data
            '''
            
            df_db = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df_db.empty:
                # Converter para o formato esperado pelo programa
                df_db['data'] = pd.to_datetime(df_db['data'])
                
                # Pivotar dados para formato de colunas
                self.df_cotacoes = df_db.pivot(index='data', columns='codigo', values='preco').reset_index()
                self.df_cotacoes.rename(columns={'data': 'Data'}, inplace=True)
                
                # Atualizar interface
                self.update_asset_combobox()
                self.btn_calculate.configure(state="normal")
                self.btn_plot.configure(state="normal")
                
                # Atualizar contador de dados
                total_ativos = len(self.df_cotacoes.columns) - 1  # -1 para excluir coluna 'Data'
                self.update_status(f"Dados carregados: {total_ativos} ativos salvos")
                
                print(f"Dados carregados do cache: {total_ativos} ativos")
            else:
                self.update_status("Nenhum dado salvo encontrado")
                
        except Exception as e:
            print(f"Erro ao carregar dados do cache: {str(e)}")
            self.update_status("Erro ao carregar dados salvos")
    
    def update_status(self, message):
        """Atualiza a barra de status"""
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.configure(text=message)

    def create_widgets(self):
        # Instrução no topo
        instruction_label = ctk.CTkLabel(self, text="1. Carregue os dados | 2. Configure inflação | 3. Calcule | 4. Visualize/Exporte", font=("Arial", 14, "bold"), anchor="center")
        instruction_label.pack(fill="x", pady=(10, 0))

        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Seção: Carregamento e Configuração ---
        top_section = ctk.CTkFrame(main_frame)
        top_section.pack(fill="x", padx=10, pady=(10, 5))

        # Título da seção
        ctk.CTkLabel(top_section, text="Carregamento e Configuração", font=("Arial", 12, "bold")).pack(anchor="nw", pady=(0, 5), padx=5)

        # Frame dos botões
        buttons_frame = ctk.CTkFrame(top_section)
        buttons_frame.pack(fill="x", padx=5, pady=(0, 5))

        self.btn_load = ctk.CTkButton(
            buttons_frame, 
            text="Carregar Arquivo XLSX",
            command=self.load_file,
            width=180
        )
        self.btn_load.pack(side="left", padx=5, pady=5)
        ToolTip(self.btn_load, "Carregue um arquivo de cotações em Excel")

        self.btn_inflation = ctk.CTkButton(
            buttons_frame, 
            text="Configurar Inflação",
            command=self.open_inflation_window,
            width=180
        )
        self.btn_inflation.pack(side="left", padx=5, pady=5)
        ToolTip(self.btn_inflation, "Defina as taxas de inflação para cada período")

        # Botão para buscar Criptomoedas (agora atualiza dados)
        self.btn_crypto = ctk.CTkButton(
            buttons_frame,
            text="🔄 Atualizar Criptomoedas",
            command=self.fetch_predefined_cryptos,
            width=180
        )
        self.btn_crypto.pack(side="left", padx=5, pady=5)
        ToolTip(self.btn_crypto, "Atualiza dados das criptomoedas da API")

        self.btn_calculate = ctk.CTkButton(
            buttons_frame, 
            text="Calcular Índices",
            command=self.calculate_indexes,
            state="disabled",
            width=180
        )
        self.btn_calculate.pack(side="left", padx=10, pady=5)
        ToolTip(self.btn_calculate, "Calcule os índices para os ativos carregados")

        self.btn_export = ctk.CTkButton(
            buttons_frame,
            text="Exportar Resultados",
            command=self.export_results,
            state="disabled",
            width=180
        )
        self.btn_export.pack(side="left", padx=5, pady=5)
        ToolTip(self.btn_export, "Exporte os resultados para Excel")

        # Frame da barra de progresso
        progress_frame = ctk.CTkFrame(top_section)
        progress_frame.pack(fill="x", padx=5, pady=(0, 5))
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=16)
        self.progress_bar.pack(fill="x", padx=5, pady=(0, 5))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove = self.progress_bar.pack_forget  # compatibilidade com chamadas existentes
        self.progress_bar.grid = self.progress_bar.pack  # compatibilidade com chamadas existentes

        # Separador visual
        sep1 = ctk.CTkLabel(main_frame, text="", height=2)
        sep1.pack(fill="x", pady=(0, 5))

        # --- Tabview principal ---
        tabview = ctk.CTkTabview(main_frame)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)
        tabview.add("Resultados")
        tabview.add("Gráfico")

        # --- Aba de Resultados ---
        results_section = ctk.CTkFrame(tabview.tab("Resultados"))
        results_section.pack(fill="both", expand=True, padx=10, pady=(0,10))
        
        # Título e contador de resultados
        header_frame = ctk.CTkFrame(results_section)
        header_frame.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(header_frame, text="Resultados dos Índices", font=("Arial", 12, "bold")).pack(side="left", padx=5, pady=5)
        self.result_count_label = ctk.CTkLabel(header_frame, text="", font=("Arial", 10))
        self.result_count_label.pack(side="right", padx=5, pady=5)

        # Frame de filtros
        filters_frame = ctk.CTkFrame(results_section)
        filters_frame.pack(fill="x", pady=(0, 5))
        
        # Título dos filtros
        ctk.CTkLabel(filters_frame, text="🔍 Filtros Avançados", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 10))
        
        # Grid de filtros (2 colunas)
        filters_grid = ctk.CTkFrame(filters_frame)
        filters_grid.pack(fill="x", padx=10, pady=(0, 10))
        
        # Coluna 1 - Filtros numéricos
        col1 = ctk.CTkFrame(filters_grid)
        col1.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Índice Melão
        melao_frame = ctk.CTkFrame(col1)
        melao_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(melao_frame, text="Índice Melão:", width=100).pack(side="left", padx=5)
        self.filtro_melao_min = ctk.CTkEntry(melao_frame, placeholder_text="Mín", width=80)
        self.filtro_melao_min.pack(side="left", padx=2)
        self.filtro_melao_max = ctk.CTkEntry(melao_frame, placeholder_text="Máx", width=80)
        self.filtro_melao_max.pack(side="left", padx=2)
        
        # Hurst
        hurst_frame = ctk.CTkFrame(col1)
        hurst_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(hurst_frame, text="Hurst (DFA):", width=100).pack(side="left", padx=5)
        self.filtro_hurst_min = ctk.CTkEntry(hurst_frame, placeholder_text="Mín", width=80)
        self.filtro_hurst_min.pack(side="left", padx=2)
        self.filtro_hurst_max = ctk.CTkEntry(hurst_frame, placeholder_text="Máx", width=80)
        self.filtro_hurst_max.pack(side="left", padx=2)
        
        # Rentabilidade
        rent_frame = ctk.CTkFrame(col1)
        rent_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(rent_frame, text="Rentabilidade (%):", width=100).pack(side="left", padx=5)
        self.filtro_rent_min = ctk.CTkEntry(rent_frame, placeholder_text="Mín", width=80)
        self.filtro_rent_min.pack(side="left", padx=2)
        self.filtro_rent_max = ctk.CTkEntry(rent_frame, placeholder_text="Máx", width=80)
        self.filtro_rent_max.pack(side="left", padx=2)
        
        # MDD
        mdd_frame = ctk.CTkFrame(col1)
        mdd_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(mdd_frame, text="MDD (%):", width=100).pack(side="left", padx=5)
        self.filtro_mdd_min = ctk.CTkEntry(mdd_frame, placeholder_text="Mín", width=80)
        self.filtro_mdd_min.pack(side="left", padx=2)
        self.filtro_mdd_max = ctk.CTkEntry(mdd_frame, placeholder_text="Máx", width=80)
        self.filtro_mdd_max.pack(side="left", padx=2)
        
        # Coluna 2 - Filtros de texto e períodos
        col2 = ctk.CTkFrame(filters_grid)
        col2.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        # Ativo
        ativo_frame = ctk.CTkFrame(col2)
        ativo_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(ativo_frame, text="Ativo:", width=80).pack(side="left", padx=5)
        self.filtro_ativo = ctk.CTkEntry(ativo_frame, placeholder_text="Nome do ativo...", width=200)
        self.filtro_ativo.pack(side="left", padx=5, fill="x", expand=True)
        
        # Períodos
        periodos_frame = ctk.CTkFrame(col2)
        periodos_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(periodos_frame, text="Períodos:", width=80).pack(side="left", padx=5)
        
        self.filtro_periodos = {
            1: ctk.BooleanVar(value=True),
            2: ctk.BooleanVar(value=True),
            3: ctk.BooleanVar(value=True),
            5: ctk.BooleanVar(value=True),
            8: ctk.BooleanVar(value=True),
            10: ctk.BooleanVar(value=True)
        }
        
        for period in [1, 2, 3, 5, 8, 10]:
            chk = ctk.CTkCheckBox(
                periodos_frame,
                text=f"{period}a",
                variable=self.filtro_periodos[period],
                command=self.aplicar_filtros,
                width=40
            )
            chk.pack(side="left", padx=2)
        
        # Botões de filtro
        buttons_filters_frame = ctk.CTkFrame(filters_frame)
        buttons_filters_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.btn_aplicar_filtros = ctk.CTkButton(
            buttons_filters_frame,
            text="✅ Aplicar Filtros",
            command=self.aplicar_filtros,
            width=120,
            fg_color="green"
        )
        self.btn_aplicar_filtros.pack(side="left", padx=5, pady=5)
        
        self.btn_limpar_filtros = ctk.CTkButton(
            buttons_filters_frame,
            text="🗑️ Limpar Filtros",
            command=self.limpar_filtros,
            width=120,
            fg_color="red"
        )
        self.btn_limpar_filtros.pack(side="left", padx=5, pady=5)
        
        self.btn_exportar_filtrados = ctk.CTkButton(
            buttons_filters_frame,
            text="📊 Exportar Filtrados",
            command=self.exportar_resultados_filtrados,
            width=150,
            fg_color="blue"
        )
        self.btn_exportar_filtrados.pack(side="right", padx=5, pady=5)
        
        # Tabela de resultados
        columns = ("Ativo", "Período", "Rentabilidade Anual (%)", "MDD (%)", 
                "MDD*", "Índice Melão", "Índice de Sharpe", "Inflação Anual (%)", "Slope", "Hurst (DFA)")
        self.tree = ttk.Treeview(
            master=results_section,
            columns=columns,
            show="headings",
            height=12
        )
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c, False))
            self.tree.column(col, width=120 if col not in ["Ativo", "Período"] else 90, anchor="center")
        scrollbar = ttk.Scrollbar(results_section, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Aba de Gráfico ---
        graph_section = ctk.CTkFrame(tabview.tab("Gráfico"), height=420)
        graph_section.pack(fill="both", expand=True, padx=10, pady=(10,10))
        ctk.CTkLabel(graph_section, text="Visualização Gráfica do Ativo", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))

        controls_frame = ctk.CTkFrame(graph_section)
        controls_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(controls_frame, text="Selecionar Ativo:").pack(side="left", padx=(10,5))

        self.asset_var = ctk.StringVar()
        self.asset_combo = ctk.CTkComboBox(
            controls_frame,
            variable=self.asset_var,
            state="disabled",
            width=120
        )
        self.asset_combo.pack(side="left", padx=5, pady=5)
        # Não adicionar tooltip aqui (CTkComboBox pode não suportar corretamente)

        self.btn_plot = ctk.CTkButton(
            controls_frame,
            text="Plotar Cotação",
            command=self.plot_asset,
            state="disabled",
            width=120
        )
        self.btn_plot.pack(side="left", padx=5, pady=5)
        ToolTip(self.btn_plot, "Exibe o gráfico do ativo selecionado")

        # Checkboxes de visualização
        self.show_cotacao = ctk.BooleanVar(value=True)
        self.show_maximas = ctk.BooleanVar(value=True)
        self.show_drawdown = ctk.BooleanVar(value=True)
        self.show_regressao = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(controls_frame, text="Cotação", variable=self.show_cotacao, command=self.plot_asset).pack(side="left", padx=5)
        ctk.CTkCheckBox(controls_frame, text="Máximas", variable=self.show_maximas, command=self.plot_asset).pack(side="left", padx=5)
        ctk.CTkCheckBox(controls_frame, text="Drawdown", variable=self.show_drawdown, command=self.plot_asset).pack(side="left", padx=5)

        periods_frame = ctk.CTkFrame(controls_frame)
        periods_frame.pack(side="left", padx=5)
        ctk.CTkLabel(periods_frame, text="Períodos:").pack(side="left", padx=(0, 5))
        for period in [10, 8, 5, 3, 2, 1]:
            chk = ctk.CTkCheckBox(
                periods_frame,
                text=f"{period}a",
                variable=self.period_vars[period],
                command=self.plot_asset,
                width=50
            )
            chk.pack(side="left", padx=(0, 2))

        # Canvas para o gráfico (mais espaçoso)
        self.figure, self.ax = plt.subplots(figsize=(12, 5))
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_section)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0,10))

        # --- Barra de status fixa no rodapé ---
        self.status_bar = ctk.CTkLabel(self, text="Pronto.", anchor="w")
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 5))

    def test_crypto_codes(self):
        """Testa quais códigos de criptomoedas são válidos na API"""
        # Lista apenas com códigos válidos confirmados
        valid_codes = [
            'BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD', 'DOGEUSD', 'TONUSD', 'ADAUSD', 
            'SHIBUSD', 'AVAXUSD', 'DOTUSD', 'TRXUSD', 'LINKUSD', 'MATICUSD', 'BCHUSD', 
            'UNIUSD', 'NEARUSD', 'LTCUSD', 'ICPUSD', 'APTUSD', 'DAIUSD', 'LEOUSD', 
            'XLMUSD', 'ETCUSD', 'OKBUSD', 'FILUSD', 'ARBUSD', 'VETUSD', 'MKRUSD', 
            'INJUSD', 'GRTUSD', 'XMRUSD', 'TIAUSD', 'SEIUSD'
        ]
        
        return valid_codes, []

    def fetch_predefined_cryptos(self):
        """Busca todas as criptomoedas pré-definidas (atualização incremental)"""
        try:
            api_key = os.getenv('apikey')
            if (not hasattr(nasdaqdatalink.ApiConfig, 'api_key') or not nasdaqdatalink.ApiConfig.api_key) and api_key:
                nasdaqdatalink.ApiConfig.api_key = api_key  # type: ignore
            
            if self.progress_bar is not None:
                self.progress_bar.pack(fill="x", padx=5, pady=(0,5))
                self.progress_bar.set(0)
            if self.status_bar is not None:
                self.status_bar.configure(text="Iniciando atualização de criptomoedas...")
            self.update()
            
            # Lista limpa de 346 criptomoedas reais (sem pares de moedas tradicionais)
            cryptos = [
                '1INCHUSD', 'AAVEUSD', 'ABSUSD', 'AGIUSD', 'AIDUSD', 'AIOUSD', 'AIXUSD', 'ALBTUSD', 'ALGUSD', 'ALT2612USD',
                'AMPUSD', 'ANCUSD', 'ANTUSD', 'APENFTUSD', 'APEUSD', 'APPUSD', 'APTUSD', 'ARBUSD', 'ASTUSD', 'ATLASUSD',
                'ATMUSD', 'ATOUSD', 'AUCUSD', 'AUSDTUSD', 'AVAXUSD', 'AVTUSD', 'AXSUSD', 'AZEROUSD', 'B21XUSD', 'B2MUSD',
                'BABUSD', 'BALUSD', 'BANDUSD', 'BATUSD', 'BBNUSD', 'BCCUSD', 'BCHABCUSD', 'BCHNUSD', 'BCHUSD', 'BCIUSD',
                'BCUUSD', 'BESTUSD', 'BFTUSD', 'BFXUSD', 'BG1USD', 'BG2USD', 'BGBUSD', 'BLURUSD', 'BMIUSD', 'BMNUSD',
                'BNTUSD', 'BOBAUSD', 'BONKUSD', 'BOOUSD', 'BORGUSD', 'BOSONUSD', 'BOXUSD', 'BRISEUSD', 'BSVUSD', 'BT1USD',
                'BT2USD', 'BTCUSD', 'BTGUSD', 'BTSEUSD', 'BTTUSD', 'CBTUSD', 'CCDUSD', 'CELOUSD', 'CELUSD', 'CFIUSD',
                'CHEXUSD', 'CHSBUSD', 'CHZUSD', 'CLOUSD', 'CNDUSD', 'CNNUSD', 'COMPUSD', 'CONVUSD', 'CRVUSD', 'CSTBCHABCUSD',
                'CSTBCHNUSD', 'CSXUSD', 'CTKUSD', 'CTXUSD', 'DADUSD', 'DAIUSD', 'DAPPUSD', 'DATUSD', 'DCRUSD', 'DGBUSD',
                'DGXUSD', 'DOGEUSD', 'DOGUSD', 'DORAUSD', 'DOTUSD', 'DRKUSD', 'DRNUSD', 'DSHUSD', 'DTAUSD', 'DTHUSD',
                'DTXUSD', 'DUSKUSD', 'DVFUSD', 'DYMUSD', 'EDOUSD', 'EGLDUSD', 'ELFUSD', 'ENJUSD', 'EOSDTUSD', 'EOSUSD',
                'ESSUSD', 'ETCUSD', 'ETH2XUSD', 'ETHUSD', 'ETHWUSD', 'ETPUSD', 'EUSUSD', 'EUTUSD', 'EVTUSD', 'EXOUSD',
                'EXRDUSD', 'FBTUSD', 'FCLUSD', 'FETUSD', 'FILUSD', 'FLOKIUSD', 'FLRUSD', 'FOAUSD', 'FORTHUSD', 'FSNUSD',
                'FTMUSD', 'FTTUSD', 'FUNUSD', 'GALAUSD', 'GENUSD', 'GMMTUSD', 'GMTUSD', 'GNOUSD', 'GNTUSD', 'GOCUSD',
                'GOMININGUSD', 'GOTUSD', 'GPTUSD', 'GRTUSD', 'GSDUSD', 'GSTUSD', 'GTXUSD', 'GXTUSD', 'HECUSD', 'HEZUSD',
                'HILSVUSD', 'HIXUSD', 'HMTUSD', 'HOTUSD', 'HTXUSD', 'ICEUSD', 'ICPUSD', 'IDXUSD', 'IMPUSD', 'INJUSD',
                'INTUSD', 'IOSUSD', 'IOTUSD', 'IQXUSD', 'JASMYUSD', 'JSTUSD', 'JUPUSD', 'KAIUSD', 'KANUSD', 'KARATEUSD',
                'KAVAUSD', 'KNCUSD', 'KSMUSD', 'LAIUSD', 'LDOUSD', 'LEOUSD', 'LIFIIIUSD', 'LINKUSD', 'LOOUSD', 'LRCUSD',
                'LTCUSD', 'LUNA2USD', 'LUNAUSD', 'LUXOUSD', 'LYMUSD', 'MANUSD', 'MATICUSD', 'MEMEUSD', 'MGOUSD', 'MIMUSD',
                'MIRUSD', 'MITUSD', 'MKRUSD', 'MLNUSD', 'MNAUSD', 'MOBUSD', 'MTNUSD', 'MXNTUSD', 'NCAUSD', 'NEARUSD',
                'NECUSD', 'NEOUSD', 'NEXOUSD', 'NIOUSD', 'NOMUSD', 'NUTUSD', 'NXRAUSD', 'OCEANUSD', 'ODEUSD', 'OGNUSD',
                'OKBUSD', 'OMGUSD', 'OMNUSD', 'ONEUSD', 'ONLUSD', 'ONUSUSD', 'OPXUSD', 'ORSUSD', 'OXYUSD', 'PAIUSD',
                'PASUSD', 'PAXUSD', 'PEPEUSD', 'PLANETSUSD', 'PLUUSD', 'PNGUSD', 'PNKUSD', 'POAUSD', 'POLCUSD', 'POLISUSD',
                'POYUSD', 'PRMXUSD', 'QRDOUSD', 'QSHUSD', 'QTFUSD', 'QTMUSD', 'RBTUSD', 'RCNUSD', 'RDNUSD', 'REEFUSD',
                'REPUSD', 'REQUSD', 'RIFUSD', 'RINGXUSD', 'RLCUSD', 'RLYUSD', 'ROSEUSD', 'RRBUSD', 'RRTUSD', 'RTEUSD',
                'SANDUSD', 'SANUSD', 'SCRUSD', 'SEEUSD', 'SEIUSD', 'SENATEUSD', 'SENUSD', 'SGBUSD', 'SHFTUSD', 'SHIBUSD',
                'SIDUSUSD', 'SMRUSD', 'SNGUSD', 'SNTUSD', 'SNXUSD', 'SOLUSD', 'SPELLUSD', 'SPKUSD', 'SRMUSD', 'STGUSD',
                'STJUSD', 'STRKUSD', 'SUIUSD', 'SUKUUSD', 'SUNUSD', 'SUSHIUSD', 'SWEATUSD', 'SWMUSD', 'SXXUSD', 'TENETUSD',
                'TERRAUSTUSD', 'THETAUSD', 'TIAUSD', 'TKNUSD', 'TLOSUSD', 'TNBUSD', 'TOMIUSD', 'TONUSD', 'TRADEUSD', 'TREEBUSD',
                'TRIUSD', 'TRXUSD', 'TSDUSD', 'TURBOUSD', 'UDCUSD', 'UFRUSD', 'UNIUSD', 'UOPUSD', 'UOSUSD', 'USKUSD',
                'USTUSD', 'UTKUSD', 'UTNUSD', 'VEEUSD', 'VELOUSD', 'VENUSD', 'VETUSD', 'VLDUSD', 'VRAUSD', 'VSYUSD',
                'WAVESUSD', 'WAXUSD', 'WBTUSD', 'WHBTUSD', 'WIFUSD', 'WILDUSD', 'WLOUSD', 'WMINIMAUSD', 'WNCGUSD', 'WOOUSD',
                'WPRUSD', 'WTCUSD', 'XAUTUSD', 'XCADUSD', 'XCHUSD', 'XCNUSD', 'XDCUSD', 'XLMUSD', 'XMRUSD', 'XRAUSD',
                'XRDUSD', 'XRPUSD', 'XSNUSD', 'XTPUSD', 'XTZUSD', 'XVGUSD', 'YFIUSD', 'YGGUSD', 'YYWUSD', 'ZBTUSD',
                'ZCNUSD', 'ZECUSD', 'ZETAUSD', 'ZILUSD', 'ZMTUSD', 'ZRXUSD'
            ]
            total = len(cryptos)
            
            for i, crypto_code in enumerate(cryptos):
                if self.status_bar is not None:
                    self.status_bar.configure(text=f"Atualizando {crypto_code} ({i+1}/{total})...")
                if self.progress_bar is not None:
                    self.progress_bar.set((i+1)/total)
                self.update()
                
                try:
                    self.fetch_crypto_data_incremental(crypto_code)
                except Exception as e:
                    # Continua mesmo se uma falhar
                    print(f"Erro em {crypto_code}: {str(e)}")
            
            if self.status_bar is not None:
                self.status_bar.configure(text=f"Atualização concluída! {total} criptomoedas processadas.")
            if self.progress_bar is not None:
                self.progress_bar.pack_forget()
            
            # Recarregar dados do banco após atualização
            self.load_cached_data()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha geral ao atualizar criptomoedas:\n{str(e)}")
            if self.progress_bar is not None:
                self.progress_bar.pack_forget()

    def fetch_crypto_data_incremental(self, crypto_code):
        """Busca dados de uma criptomoeda com atualização incremental"""
        try:
            # Verificar última data salva
            last_date = self.get_last_update_date(crypto_code)
            
            # Definir data de início para busca
            if last_date:
                start_date = last_date + timedelta(days=1)
            else:
                # Buscar todos os dados históricos disponíveis (sem limite)
                start_date = None
            
            # Buscar dados da API (todos os dados disponíveis)
            df_crypto = nasdaqdatalink.get_table(
                'QDL/BITFINEX', 
                code=crypto_code,
                paginate=True
            )
            
            # Verificar se a coluna de data existe
            date_column = 'date' if 'date' in df_crypto.columns else 'Date'
            
            # Selecionar colunas relevantes
            df_crypto = df_crypto[[date_column, 'mid']]
            df_crypto.columns = ['Data', crypto_code]
            
            # Converter datas e ordenar
            df_crypto['Data'] = pd.to_datetime(df_crypto['Data'])
            df_crypto.sort_values('Data', inplace=True)
            
            # Filtrar apenas dados mais recentes que o último salvo (se houver dados salvos)
            if last_date:
                df_crypto = df_crypto[df_crypto['Data'].dt.date > last_date]
            
            # Salvar no banco de dados
            if not df_crypto.empty:
                self.save_crypto_data_to_db(crypto_code, df_crypto)
            
        except Exception as e:
            print(f"Erro ao buscar {crypto_code}: {str(e)}")
            raise e
    
    def update_asset_combobox(self):
        """Atualiza a lista de ativos no combobox com base no DataFrame de cotações."""
        if self.df_cotacoes is not None:
            # Obter todos os nomes de colunas exceto 'Data'
            ativos = [col for col in self.df_cotacoes.columns if col != 'Data']
            
            # Atualizar combobox
            self.asset_combo.configure(values=ativos)
            
            # Configurar seleção inicial se houver ativos
            if ativos:
                current_value = self.asset_var.get()
                if current_value not in ativos:
                    self.asset_var.set(ativos[0])
                self.asset_combo.configure(state="readonly")
                self.btn_plot.configure(state="normal")
            else:
                self.asset_combo.configure(state="disabled")
                self.btn_plot.configure(state="disabled")
                
    def load_file(self):
        file_path = ctk.filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx")]
        )
        
        if file_path:
            try:
                self.df_cotacoes = pd.read_excel(file_path, parse_dates=[0])
                first_col = self.df_cotacoes.columns[0]
                self.df_cotacoes.rename(columns={str(first_col): 'Data'}, inplace=True)
                
                # Atualizar combobox de ativos usando o novo método
                self.update_asset_combobox()
                
                self.btn_calculate.configure(state="normal")
                messagebox.showinfo("Sucesso", f"Arquivo carregado: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Falha", f"Erro ao carregar arquivo: {str(e)}")
    
    def open_inflation_window(self):
        if self.inflation_window and self.inflation_window.winfo_exists():
            self.inflation_window.lift()
            return
            
        self.inflation_window = ctk.CTkToplevel(self)
        self.inflation_window.title("Configurar Taxas de Inflação")
        self.inflation_window.geometry("400x400")
        self.inflation_window.transient(self)
        self.inflation_window.grab_set()
        self.inflation_window.protocol("WM_DELETE_WINDOW", self.close_inflation_window)
        
        # Frame principal
        main_frame = ctk.CTkFrame(self.inflation_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título
        ctk.CTkLabel(
            main_frame, 
            text="Configurar Taxas de Inflação Acumulada (%)",
            font=("Arial", 14, "bold")
        ).pack(pady=(5, 15))
        
        # Frame para as entradas
        entries_frame = ctk.CTkFrame(main_frame)
        entries_frame.pack(fill="x", padx=20, pady=5)
        
        # Dicionário para armazenar as entradas
        self.inflation_entries = {}
        
        # Períodos desejados
        periods = [10, 8, 5, 3, 2, 1]
        
        # Criar entradas para cada período
        for i, period in enumerate(periods):
            row_frame = ctk.CTkFrame(entries_frame)
            row_frame.pack(fill="x", padx=5, pady=5)
            
            ctk.CTkLabel(
                row_frame, 
                text=f"{period} anos:",
                width=80
            ).pack(side="left", padx=(10, 5))
            
            entry = ctk.CTkEntry(row_frame, width=100)
            entry.pack(side="left", padx=(0, 10))
            self.inflation_entries[period] = entry
        
        # Carregar valores atuais
        self.load_inflation_to_entries()
        
        # Frame para botões
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", padx=10, pady=20)
        
        # Botão Salvar
        btn_save = ctk.CTkButton(
            buttons_frame,
            text="Salvar Inflação",
            command=self.save_inflation_from_window
        )
        btn_save.pack(side="right", padx=10)
        
        # Botão Cancelar
        btn_cancel = ctk.CTkButton(
            buttons_frame,
            text="Cancelar",
            command=self.close_inflation_window
        )
        btn_cancel.pack(side="right", padx=10)
    
    def close_inflation_window(self):
        if self.inflation_window and self.inflation_window.winfo_exists():
            self.inflation_window.grab_release()
            self.inflation_window.destroy()
        self.inflation_window = None
    
    def load_inflation_to_entries(self):
        for period, entry in self.inflation_entries.items():
            value = self.inflacao.get(period, 0.0) * 100
            entry.delete(0, 'end')
            entry.insert(0, str(round(value, 2)))
    
    def save_inflation_main(self):
        try:
            inflation_to_save = {str(k): v * 100 for k, v in self.inflacao.items()}
            
            with open(self.json_file, 'w') as f:
                json.dump(inflation_to_save, f, indent=4)
            
            messagebox.showinfo("Sucesso", "Inflação salva com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar inflação: {str(e)}")
    
    def save_inflation_from_window(self):
        try:
            for period, entry in self.inflation_entries.items():
                try:
                    value = float(entry.get())
                    self.inflacao[period] = value / 100.0
                except ValueError:
                    pass
            
            self.save_inflation_main()
            self.close_inflation_window()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar inflação: {str(e)}")
    
    def load_inflation(self):
        try:
            if os.path.exists(self.json_file):
                with open(self.json_file, 'r') as f:
                    saved_inflation = json.load(f)
                    for period in self.inflacao.keys():
                        if str(period) in saved_inflation:
                            value = float(saved_inflation[str(period)])
                            self.inflacao[period] = value / 100.0
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar inflação: {str(e)}")
             
    def export_results(self):
        if not self.current_results:
            messagebox.showerror("Erro", "Nenhum resultado para exportar")
            return
            
        try:
            file_path = ctk.filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")]
            )
            
            if file_path:
                import pandas
                df = pandas.DataFrame(self.current_results, 
                                 columns=["Ativo", "Período", "Rentabilidade Anual (%)", "MDD (%)", 
                                        "MDD*", "Índice Melão", "Índice de Sharpe", "Inflação Anual (%)", "Slope", "Hurst (DFA)"])  # type: ignore
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Sucesso", f"Resultados exportados para {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar resultados: {str(e)}")
    
    def plot_asset(self):
        if self.df_cotacoes is None or self.asset_var.get() == "":
            return
            
        try:
            ativo = self.asset_var.get()
            df_ativo = self.df_cotacoes[['Data', ativo]].dropna(subset=[ativo]).copy()  # type: ignore
            
            if len(df_ativo) < 1:
                return
                
            min_data = df_ativo['Data'].min()
            max_data = df_ativo['Data'].max()
            
            self.ax.clear()
            
            if self.show_cotacao.get():
                self.ax.plot(df_ativo['Data'], df_ativo[ativo], color='#1f77b4', linewidth=1.5, label='Cotação')
            
            if self.show_regressao.get():
                period_colors = {10: 'red', 8: 'gray', 5: 'purple', 3: 'cyan', 2: 'orange', 1: 'green'}
                
                for periodo in [10, 8, 5, 3, 2, 1]:
                    if not self.period_vars[periodo].get():
                        continue  # Pula períodos não selecionados
                    data_inicio = max_data - timedelta(days=periodo*365)
                    df_periodo = df_ativo[(df_ativo['Data'] >= data_inicio) & (df_ativo['Data'] <= max_data)]
                    
                    if len(df_periodo) < 3:
                        continue
                        
                    try:
                        df_reg = df_periodo.copy()
                        df_reg['Dias'] = (df_reg['Data'] - df_reg['Data'].min()).dt.days  # type: ignore
                        df_reg['LogPreco'] = np.log(df_reg[ativo])
                        
                        slope, intercept = np.polyfit(df_reg['Dias'], df_reg['LogPreco'], 1)
                        df_reg['Regressao'] = np.exp(slope * df_reg['Dias'] + intercept)
                        
                        self.ax.plot(df_reg['Data'], df_reg['Regressao'], 
                                    color=period_colors[periodo], linestyle='--', linewidth=2, 
                                    label=f'Cotação {periodo}a')
                        
                    except Exception as reg_error:
                        print(f"Erro na regressão {periodo}a: {reg_error}")
            
            if self.show_maximas.get():
                df_ativo['Maximo'] = df_ativo[ativo].cummax()
                self.ax.plot(df_ativo['Data'], df_ativo['Maximo'], color='#ff7f0e', 
                            linestyle='--', alpha=0.7, label='Máximas')
            
            if self.show_drawdown.get():
                if 'Maximo' not in df_ativo.columns:
                    df_ativo['Maximo'] = df_ativo[ativo].cummax()
                df_ativo['Drawdown'] = df_ativo[ativo] / df_ativo['Maximo'] - 1
                self.ax.fill_between(df_ativo['Data'], df_ativo[ativo], df_ativo['Maximo'], 
                                    where=(df_ativo[ativo] < df_ativo['Maximo']),
                                    facecolor='red', alpha=0.3, label='Drawdown')
            
            self.ax.set_title(f"Cotação de {ativo} ({min_data.date()} a {max_data.date()})", fontsize=12)
            self.ax.set_xlabel("Data")
            self.ax.set_ylabel("Preço")
            self.ax.set_xlim(min_data, max_data)
            # type: ignore
            self.figure.autofmt_xdate()
            self.ax.grid(True, linestyle='--', alpha=0.7)
            self.ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
            self.figure.tight_layout(rect=(0, 0, 0.85, 1))
            
            self.canvas.draw()
            update_id = self.after(100, self.check_plot_update)
            self.after_ids.append(update_id)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao plotar ativo: {str(e)}")
    
    def check_plot_update(self):
        if hasattr(self, 'canvas') and self.winfo_exists():
            try:
                self.canvas.draw()
            except tk.TclError:
                pass
    
    def calculate_rentabilidade(self, df_periodo, ativo, periodo_anos):
        try:
            df = df_periodo[['Data', ativo]].dropna(subset=[ativo])
            if len(df) < 2:
                return None
            
            min_data = df['Data'].min()
            df['Dias'] = (df['Data'] - min_data).dt.days
            
            x = df['Dias'].values
            y = np.log(df[ativo].values)
            regressao = linregress(x, y)
            
            rentabilidade_anual = np.exp(regressao.slope*365) - 1 # type: ignore
            
            return rentabilidade_anual, regressao.slope
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro no cálculo de rentabilidade: {str(e)}")
            return None
    
    def calculate_hurst_dfa(self, series):
        """Calcula o expoente de Hurst usando Detrended Fluctuation Analysis (DFA)"""
        try:
            # Se a biblioteca nolds estiver disponível, use-a
            if 'nolds' in globals():
                return nolds.dfa(series)
            
            # Implementação manual como fallback
            n = len(series)
            scales = np.logspace(np.log10(4), np.log10(n//4), 20, dtype=int)
            
            fluctuations = []
            for scale in scales:
                rms = []
                for i in range(0, n - scale + 1, scale // 2):
                    segment = series[i:i+scale]
                    x = np.arange(scale)
                    coef = np.polyfit(x, segment, 1)
                    trend = np.polyval(coef, x)
                    rms.append(np.sqrt(np.mean((segment - trend)**2)))
                
                fluctuations.append(np.log(np.mean(rms)))
            
            hurst, _ = np.polyfit(np.log(scales), fluctuations, 1)
            return hurst
        except Exception as e:
            print(f"Erro no cálculo DFA: {str(e)}")
            return np.nan
    
    def calculate_indexes(self):
        if self.df_cotacoes is None:
            return
            
        try:
            if self.progress_bar is not None:
                self.progress_bar.pack(fill="x", padx=5, pady=(0,5))
                self.progress_bar.start()
            self.btn_calculate.configure(state="disabled")
            self.btn_export.configure(state="disabled")
            if self.status_bar is not None:
                self.status_bar.configure(text="Calculando índices...")
            self.update()
            
            resultados = []
            ativos = self.df_cotacoes.columns[1:]
            data_final = self.df_cotacoes['Data'].max()
            
            total_ativos = len(ativos)
            ativos_processados = 0
            
            for ativo in ativos:
                ativos_processados += 1
                if self.status_bar is not None:
                    self.status_bar.configure(text=f"Calculando {ativo} ({ativos_processados}/{total_ativos})...")
                self.update()

                df_ativo = self.df_cotacoes[['Data', ativo]].dropna(subset=[ativo])  # type: ignore
                if df_ativo.empty:
                    continue
                
                # NOVA VERIFICAÇÃO: só processa se o ativo tiver dados até pelo menos uma semana antes da data final
                data_mais_recente = df_ativo['Data'].max()
                if data_mais_recente < (data_final - timedelta(days=7)):
                    continue
                
                min_data_ativo = df_ativo['Data'].min()
                
                for periodo in [10, 8, 5, 3, 2, 1]:
                    data_inicio = data_final - timedelta(days=periodo*365)
                    
                    if min_data_ativo > data_inicio:
                        continue
                        
                    df_periodo = self.df_cotacoes[
                        (self.df_cotacoes['Data'] >= data_inicio) & 
                        (self.df_cotacoes['Data'] <= data_final)
                    ].copy()
                    
                    if df_periodo.empty or df_periodo[ativo].isnull().all():  # type: ignore
                        continue
                        
                    df_periodo[ativo] = df_periodo[ativo].ffill().bfill()  # type: ignore
                    
                    # Calcular rentabilidade anual média
                    resultado_rent = self.calculate_rentabilidade(df_periodo, ativo, periodo)
                    if resultado_rent is None:
                        continue
                    
                    rentabilidade_anual, coef_angular = resultado_rent
                    
                    # Calcular MDD
                    df_periodo['Maximo'] = df_periodo[ativo].cummax()  # type: ignore
                    df_periodo['Drawdown'] = (df_periodo[ativo] / df_periodo['Maximo']) - 1
                    mdd_valor = df_periodo['Drawdown'].min()
                    mdd_abs = abs(mdd_valor)
                    mdd_star = mdd_abs / (1 - mdd_abs)
                    
                    # Converter inflação acumulada para anual média
                    infl_acumulada = self.inflacao[periodo]
                    inflacao_anual = ((1 + infl_acumulada) ** (1/periodo)) - 1
                    
                    # Calcular Índice Melão
                    numerador = np.log(1 + rentabilidade_anual) - np.log(1 + inflacao_anual)
                    denominador = np.log(1 + mdd_star) / np.sqrt(periodo)
                    
                    if denominador == 0:
                        indice_melao = 0
                    else:
                        indice_melao = (numerador / denominador)
                    
                    # Calcular Índice de Sharpe
                    taxa_livre_risco = 0.10  # 10% ao ano
                    # Calcular retornos diários
                    try:
                        prices_sharpe = df_periodo[ativo].dropna().values
                        if len(prices_sharpe) > 1:
                            log_prices_sharpe = np.log(prices_sharpe)
                            retornos_diarios = np.diff(log_prices_sharpe)
                            media_retorno_diario = np.mean(retornos_diarios)
                            std_retorno_diario = np.std(retornos_diarios)
                            # Ajustar para anual
                            sharpe = ((media_retorno_diario * 252) - taxa_livre_risco) / (std_retorno_diario * np.sqrt(252)) if std_retorno_diario > 0 else 0
                        else:
                            sharpe = 0
                    except Exception as e:
                        sharpe = 0
                    
                    # CALCULAR AMBOS OS EXPONENTES DE HURST
                    hurst_dfa = np.nan
                    
                    try:
                        prices = df_periodo[ativo].dropna().values  # type: ignore
                        
                        if len(prices) > 100:  # Mínimo necessário para cálculos confiáveis
                            # Calcular retornos logarítmicos
                            log_prices = np.log(prices)
                            returns = np.diff(log_prices)
                            
                            # Remover NaNs e infinitos
                            returns = returns[~np.isnan(returns)]
                            returns = returns[np.isfinite(returns)]
                            
                            if len(returns) >= 100:
                                hurst_dfa = self.calculate_hurst_dfa(returns)
                    except Exception as e:
                        print(f"Erro cálculo Hurst {ativo}: {str(e)}")

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
                        f"{hurst_dfa:.4f}" if not np.isnan(hurst_dfa) else "N/A"  # type: ignore
                    ])
            
            self.current_results = resultados
            self.update_table(resultados)
            self.btn_export.configure(state="normal")
            if self.status_bar is not None:
                self.status_bar.configure(text="Cálculos concluídos com sucesso!")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro nos cálculos: {str(e)}")
            if self.status_bar is not None:
                self.status_bar.configure(text="Erro ao calcular.")
        finally:
            try:
                if self.progress_bar is not None:
                    self.progress_bar.stop()
                    self.progress_bar.pack_forget()
            except Exception:
                pass
            
            try:
                self.btn_calculate.configure(state="normal")
                self.update()
            except Exception:
                pass

    def update_table(self, resultados):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for row in resultados:
            self.tree.insert("", "end", values=row)

    def sort_by_column(self, col, reverse):
        # Obter todos os itens da tabela
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        # Tentar converter para float para ordenação numérica
        try:
            l.sort(key=lambda t: float(t[0].replace('%','').replace('*','').replace('N/A','-9999')), reverse=reverse)
        except Exception:
            l.sort(reverse=reverse)
        # Rearranjar itens na treeview
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
        # Alternar ordem para o próximo clique
        self.tree.heading(col, command=lambda: self.sort_by_column(col, not reverse))

    def aplicar_filtros(self):
        """Aplica os filtros selecionados na tabela"""
        if not self.current_results:
            return
            
        try:
            # Obter valores dos filtros
            filtros = {
                'melao_min': self.get_float_value(self.filtro_melao_min.get()),
                'melao_max': self.get_float_value(self.filtro_melao_max.get()),
                'hurst_min': self.get_float_value(self.filtro_hurst_min.get()),
                'hurst_max': self.get_float_value(self.filtro_hurst_max.get()),
                'rent_min': self.get_float_value(self.filtro_rent_min.get()),
                'rent_max': self.get_float_value(self.filtro_rent_max.get()),
                'mdd_min': self.get_float_value(self.filtro_mdd_min.get()),
                'mdd_max': self.get_float_value(self.filtro_mdd_max.get()),
                'ativo': self.filtro_ativo.get().strip().lower(),
                'periodos': [p for p, var in self.filtro_periodos.items() if var.get()]
            }
            
            # Filtrar resultados
            resultados_filtrados = []
            for resultado in self.current_results:
                if self.passa_filtros(resultado, filtros):
                    resultados_filtrados.append(resultado)
            
            # Atualizar tabela
            self.update_table(resultados_filtrados)
            
            # Atualizar contador
            total = len(self.current_results)
            filtrados = len(resultados_filtrados)
            self.result_count_label.configure(
                text=f"Mostrando {filtrados} de {total} resultados"
            )
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao aplicar filtros: {str(e)}")
    
    def get_float_value(self, value):
        """Converte string para float, retorna None se inválido"""
        if not value or value.strip() == '':
            return None
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            return None
    
    def passa_filtros(self, resultado, filtros):
        """Verifica se um resultado passa pelos filtros aplicados"""
        try:
            # Índice Melão
            melao = float(resultado[5])  # Índice Melão está na posição 5
            if filtros['melao_min'] is not None and melao < filtros['melao_min']:
                return False
            if filtros['melao_max'] is not None and melao > filtros['melao_max']:
                return False
            
            # Hurst
            hurst_str = resultado[8]  # Hurst está na posição 8
            if hurst_str != "N/A":
                hurst = float(hurst_str)
                if filtros['hurst_min'] is not None and hurst < filtros['hurst_min']:
                    return False
                if filtros['hurst_max'] is not None and hurst > filtros['hurst_max']:
                    return False
            
            # Rentabilidade
            rent = float(resultado[2].replace('%', ''))  # Rentabilidade está na posição 2
            if filtros['rent_min'] is not None and rent < filtros['rent_min']:
                return False
            if filtros['rent_max'] is not None and rent > filtros['rent_max']:
                return False
            
            # MDD
            mdd = float(resultado[3].replace('%', ''))  # MDD está na posição 3
            if filtros['mdd_min'] is not None and mdd < filtros['mdd_min']:
                return False
            if filtros['mdd_max'] is not None and mdd > filtros['mdd_max']:
                return False
            
            # Ativo
            if filtros['ativo']:
                ativo = resultado[0].lower()  # Ativo está na posição 0
                if filtros['ativo'] not in ativo:
                    return False
            
            # Períodos
            periodo = resultado[1]  # Período está na posição 1
            periodo_anos = int(periodo.split()[0])  # Extrair número do período
            if periodo_anos not in filtros['periodos']:
                return False
            
            return True
            
        except Exception as e:
            print(f"Erro ao verificar filtros: {str(e)}")
            return False
    
    def limpar_filtros(self):
        """Limpa todos os filtros e mostra todos os resultados"""
        # Limpar campos
        self.filtro_melao_min.delete(0, 'end')
        self.filtro_melao_max.delete(0, 'end')
        self.filtro_hurst_min.delete(0, 'end')
        self.filtro_hurst_max.delete(0, 'end')
        self.filtro_rent_min.delete(0, 'end')
        self.filtro_rent_max.delete(0, 'end')
        self.filtro_mdd_min.delete(0, 'end')
        self.filtro_mdd_max.delete(0, 'end')
        self.filtro_ativo.delete(0, 'end')
        
        # Marcar todos os períodos
        for var in self.filtro_periodos.values():
            var.set(True)
        
        # Mostrar todos os resultados
        self.update_table(self.current_results)
        total = len(self.current_results) if self.current_results else 0
        self.result_count_label.configure(text=f"Mostrando {total} de {total} resultados")
    
    def exportar_resultados_filtrados(self):
        """Exporta apenas os resultados filtrados"""
        if not self.current_results:
            messagebox.showerror("Erro", "Nenhum resultado para exportar")
            return
        
        try:
            # Obter resultados filtrados atuais
            items = self.tree.get_children()
            resultados_filtrados = []
            for item in items:
                valores = self.tree.item(item)['values']
                resultados_filtrados.append(valores)
            
            if not resultados_filtrados:
                messagebox.showerror("Erro", "Nenhum resultado filtrado para exportar")
                return
            
            file_path = ctk.filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")]
            )
            
            if file_path:
                import pandas
                df = pandas.DataFrame(resultados_filtrados, 
                                 columns=["Ativo", "Período", "Rentabilidade Anual (%)", "MDD (%)", 
                                        "MDD*", "Índice Melão", "Índice de Sharpe", "Inflação Anual (%)", "Slope", "Hurst (DFA)"])  # type: ignore
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Sucesso", f"Resultados filtrados exportados para {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar resultados filtrados: {str(e)}")

if __name__ == "__main__":
    app = MelaoIndexApp()
    app.mainloop()