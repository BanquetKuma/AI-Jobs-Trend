# -*- coding: utf-8 -*-
"""技術キーワード正規化辞書。

TECHS の各エントリは (正規化名, カテゴリ, 検出用正規表現) の3つ組。
正規表現は re.IGNORECASE でコンパイルされる。

短いASCIIトークン（R, Go, SQL 等）は誤検出しやすいので、
前後の文字クラスを明示的に縛った表現にしてある。
"""

# (name, category, pattern)
TECHS = [
    # ---- 言語 ----
    ("Python",      "プログラミング言語", r"Python"),
    ("R",           "プログラミング言語", r"(?<![0-9A-Za-z_&])R(?![0-9A-Za-z_&])"),
    ("TypeScript",  "プログラミング言語", r"TypeScript|\bTS\b"),
    ("JavaScript",  "プログラミング言語", r"JavaScript"),
    ("Kotlin",      "プログラミング言語", r"Kotlin"),
    ("Java",        "プログラミング言語", r"(?<![0-9A-Za-z_])Java(?!Script)"),
    ("Go",          "プログラミング言語", r"(?<![0-9A-Za-z_])(?:Go|Golang)(?![0-9A-Za-z_])"),
    ("C#/.NET",     "プログラミング言語", r"C#|\.NET"),
    ("Scala",       "プログラミング言語", r"Scala"),
    ("SQL",         "プログラミング言語", r"(?<![0-9A-Za-z_])SQL(?![0-9A-Za-z_])"),
    ("VBA",         "プログラミング言語", r"(?<![0-9A-Za-z_])VBA(?![0-9A-Za-z_])"),

    # ---- クラウド ----
    ("AWS",             "クラウド基盤", r"(?<![0-9A-Za-z_])AWS(?![0-9A-Za-z_])|Amazon Web Services"),
    ("Azure",           "クラウド基盤", r"Azure"),
    ("GCP",             "クラウド基盤", r"(?<![0-9A-Za-z_])GCP(?![0-9A-Za-z_])|Google Cloud"),
    ("Azure AI Foundry","クラウド基盤", r"Azure\s*AI\s*Foundry|AI\s*Foundry"),
    ("Azure OpenAI",    "クラウド基盤", r"Azure\s*OpenAI"),
    ("Amazon Bedrock",  "クラウド基盤", r"Bedrock"),
    ("Vertex AI",       "クラウド基盤", r"Vertex\s*AI"),
    ("SAP BTP",         "クラウド基盤", r"(?<![0-9A-Za-z_])BTP(?![0-9A-Za-z_])|Business Technology Platform"),
    ("Kubernetes",      "クラウド基盤", r"Kubernetes|(?<![0-9A-Za-z_])K8s(?![0-9A-Za-z_])|(?<![0-9A-Za-z_])EKS(?![0-9A-Za-z_])|(?<![0-9A-Za-z_])AKS(?![0-9A-Za-z_])"),
    ("Terraform",       "クラウド基盤", r"Terraform"),

    # ---- データ基盤 ----
    ("Databricks",  "データ基盤", r"Databricks"),
    ("Snowflake",   "データ基盤", r"Snowflake"),
    ("BigQuery",    "データ基盤", r"BigQuery"),
    ("Redshift",    "データ基盤", r"Redshift"),
    ("PostgreSQL",  "データ基盤", r"PostgreSQL|Postgres"),
    ("MySQL",       "データ基盤", r"MySQL"),
    ("Oracle",      "データ基盤", r"(?<![0-9A-Za-z_])Oracle(?![0-9A-Za-z_])"),
    ("Power BI",    "データ基盤", r"Power\s*[-‐–—]?\s*BI"),
    ("Tableau",     "データ基盤", r"Tableau"),
    ("Looker",      "データ基盤", r"Looker"),
    ("dbt",         "データ基盤", r"(?<![0-9A-Za-z_])dbt(?![0-9A-Za-z_])"),
    ("Spark",       "データ基盤", r"(?<![0-9A-Za-z_])(?:Apache\s*)?Spark(?![0-9A-Za-z_])|PySpark"),
    ("ETL",         "データ基盤", r"(?<![0-9A-Za-z_])ETL(?![0-9A-Za-z_])|(?<![0-9A-Za-z_])ELT(?![0-9A-Za-z_])"),
    ("DWH",         "データ基盤", r"(?<![0-9A-Za-z_])DWH(?![0-9A-Za-z_])|データウェアハウス|データレイク|Data\s*Lake"),
    ("ベクトルDB",  "データ基盤", r"ベクトル\s*(?:DB|データベース)|ベクタ\s*(?:DB|検索)|Vector\s*(?:DB|Search|Store)|Pinecone|Weaviate|Qdrant|Chroma"),

    # ---- 生成AI ----
    ("生成AI",                    "生成AI", r"生成\s*AI|ジェネレーティブ\s*AI|Generative\s*AI"),
    ("LLM",                       "生成AI", r"(?<![0-9A-Za-z_])LLM(?![0-9A-Za-z_])|大規模言語モデル"),
    ("RAG",                       "生成AI", r"(?<![0-9A-Za-z_])RAG(?![0-9A-Za-z_])|検索拡張生成"),
    ("AIエージェント",            "生成AI", r"AI\s*(?:エージェント|Agent)|エージェンティック|Agentic"),
    ("プロンプトエンジニアリング","生成AI", r"プロンプト(?:設計|エンジニアリング|の構造化|チューニング)"),
    ("コンテキストエンジニアリング","生成AI", r"コンテキスト\s*エンジニアリング|Context\s*Engineering"),
    ("ファインチューニング",      "生成AI", r"ファインチューニング|Fine[-\s]?tuning|(?<![0-9A-Za-z_])SFT(?![0-9A-Za-z_])|LoRA"),
    ("LLM評価",                   "生成AI", r"LLM[-\s]?as[-\s]?a[-\s]?Judge|評価データセット|オフライン評価|精度評価|LLM\s*評価"),
    ("MCP",                       "生成AI", r"(?<![0-9A-Za-z_])MCP(?![0-9A-Za-z_])|Model\s*Context\s*Protocol"),
    ("マルチモーダル",            "生成AI", r"マルチモーダル|Multimodal"),
    ("OpenAI API",                "生成AI", r"OpenAI|ChatGPT|GPT-[45]"),
    ("Claude",                    "生成AI", r"(?<![0-9A-Za-z_])Claude(?!\s*Code)"),
    ("Gemini",                    "生成AI", r"(?<![0-9A-Za-z_])Gemini(?![0-9A-Za-z_])"),
    ("LangChain",                 "生成AI", r"LangChain|LangGraph|LlamaIndex"),
    ("AIガバナンス",              "生成AI", r"AI\s*ガバナンス|AI\s*ガイドライン|AI\s*品質保証|AI\s*セキュリティ|統制(?:方針|ルール|ガイドライン)"),

    # ---- AI活用ツール ----
    ("Claude Code",     "AI開発ツール", r"Claude\s*Code"),
    ("GitHub Copilot",  "AI開発ツール", r"GitHub\s*Copilot"),
    ("Copilot Studio",  "AI開発ツール", r"Copilot\s*Studio"),
    ("Microsoft 365 Copilot", "AI開発ツール", r"(?:Microsoft\s*)?365\s*Copilot|M365\s*Copilot"),
    ("Cursor",          "AI開発ツール", r"(?<![0-9A-Za-z_])Cursor(?![0-9A-Za-z_])"),
    ("Dify",            "AI開発ツール", r"(?<![0-9A-Za-z_])Dify(?![0-9A-Za-z_])"),
    ("AIコーディング支援","AI開発ツール", r"AIコーディング|AI支援ツール|AI\s*コーディングエージェント"),
    ("Power Platform",  "AI開発ツール", r"Power\s*Platform|Power\s*Apps|Power\s*Automate"),
    ("RPA",             "AI開発ツール", r"(?<![0-9A-Za-z_])RPA(?![0-9A-Za-z_])|UiPath|WinActor"),

    # ---- 機械学習 ----
    ("機械学習",    "機械学習", r"機械学習|Machine\s*Learning|(?<![0-9A-Za-z_])ML(?![0-9A-Za-z_])"),
    ("深層学習",    "機械学習", r"深層学習|ディープラーニング|Deep\s*Learning"),
    ("PyTorch",     "機械学習", r"PyTorch"),
    ("TensorFlow",  "機械学習", r"TensorFlow|Keras"),
    ("scikit-learn","機械学習", r"scikit[-\s]?learn|sklearn"),
    ("pandas/NumPy","機械学習", r"Pandas|NumPy"),
    ("時系列分析",  "機械学習", r"時系列"),
    ("異常検知",    "機械学習", r"異常検知"),
    ("因果推論",    "機械学習", r"因果推論|ベイズ|統計解析|統計的"),
    ("自然言語処理","機械学習", r"自然言語処理|(?<![0-9A-Za-z_])NLP(?![0-9A-Za-z_])"),
    ("画像認識",    "機械学習", r"画像認識|画像処理|物体検出|コンピュータビジョン|動作解析|姿勢推定"),
    ("需要予測",    "機械学習", r"需要予測|予測モデル"),
    ("レコメンド",  "機械学習", r"レコメンド|推薦"),

    # ---- 基盤・運用 ----
    ("Docker",          "開発基盤・運用", r"Docker|コンテナ"),
    ("MLOps",           "開発基盤・運用", r"MLOps|LLMOps"),
    ("CI/CD",           "開発基盤・運用", r"CI\s*/\s*CD|継続的インテグレーション"),
    ("GitHub Actions",  "開発基盤・運用", r"GitHub\s*Actions"),
    ("Git",             "開発基盤・運用", r"(?<![0-9A-Za-z_])Git(?![0-9A-Za-zH_])"),
    ("監視・可観測性",  "開発基盤・運用", r"OpenTelemetry|可観測性|Observability|Datadog"),
    ("DevOps",          "開発基盤・運用", r"DevOps"),

    # ---- 業務・その他 ----
    ("React",           "アプリ開発", r"(?<![0-9A-Za-z_])React(?![0-9A-Za-z_])"),
    ("Vue",             "アプリ開発", r"(?<![0-9A-Za-z_])Vue(?![0-9A-Za-z_])"),
    ("API設計",         "アプリ開発", r"(?<![0-9A-Za-z_])API(?![0-9A-Za-z_])|REST|GraphQL"),
    ("SAP",             "業務システム", r"(?<![0-9A-Za-z_])SAP(?![0-9A-Za-z_])"),
    ("Salesforce",      "業務システム", r"Salesforce|Agentforce"),
    ("ERP",             "業務システム", r"(?<![0-9A-Za-z_])ERP(?![0-9A-Za-z_])"),
    ("SCM",             "業務システム", r"(?<![0-9A-Za-z_])SCM(?![0-9A-Za-z_])|需給管理|在庫管理"),
    ("CRM",             "業務システム", r"(?<![0-9A-Za-z_])CRM(?![0-9A-Za-z_])"),
    ("PMO",             "進め方・プロセス", r"(?<![0-9A-Za-z_])PMO(?![0-9A-Za-z_])"),
    ("要件定義",        "進め方・プロセス", r"要件定義"),
    ("PoC",             "進め方・プロセス", r"(?<![0-9A-Za-z_])PoC(?![0-9A-Za-z_])|実証実験"),
    ("アジャイル",      "進め方・プロセス", r"アジャイル|スクラム|Scrum"),
    ("英語",            "進め方・プロセス", r"英語"),
]

# 稼働形態の正規化
WORKSTYLE_RULES = [
    ("リモート・オンサイト併用", r"併用"),
    ("常駐",                     r"常駐"),
    ("フルリモート",             r"リモート"),
    ("オンサイト",               r"オンサイト|出社"),
]

# ポジションの正規化（[ポジション] フィールドの表記ゆれを束ねる）
POSITION_RULES = [
    ("AIエンジニア",        r"AI\s*エンジニア|機械学習エンジニア|MLエンジニア"),
    ("データサイエンティスト", r"データサイエンティスト"),
    ("データアナリスト",    r"データアナリスト|アナリスト"),
    ("データエンジニア",    r"データエンジニア|分析基盤エンジニア|データ基盤"),
    ("BIエンジニア",        r"BI\s*エンジニア"),
    ("AI導入コンサル",      r"AI\s*導入コンサル|AIコンサル"),
    ("ITコンサル",          r"IT\s*コンサル|コンサル"),
    ("PM/PdM",              r"(?<![0-9A-Za-z_])PM(?![0-9A-Za-z_])|(?<![0-9A-Za-z_])PdM(?![0-9A-Za-z_])|プロジェクトマネージャ|プロダクトマネージャ|PMO"),
    ("バックエンドエンジニア", r"バックエンド|サーバーサイド"),
    ("フロントエンドエンジニア", r"フロントエンド"),
    ("インフラエンジニア",  r"インフラ|SRE|クラウドエンジニア"),
    ("アプリエンジニア",    r"アプリケーションエンジニア|開発エンジニア|エンジニア"),
]
