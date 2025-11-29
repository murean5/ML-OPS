"""Streamlit дашборд для ML Service."""

import streamlit as st
import pandas as pd
import json
import requests
import os
from typing import Dict, Any, List
import io

DOCKER_API_URL = os.getenv("API_BASE_URL", "http://ml-api:8000")
BROWSER_API_URL = os.getenv("BROWSER_API_URL", "http://localhost:8000")
IS_DOCKER = os.path.exists("/.dockerenv")
DEFAULT_URL = DOCKER_API_URL if IS_DOCKER else BROWSER_API_URL

API_BASE_URL = st.sidebar.text_input(
    "API URL", 
    value=DEFAULT_URL, 
    help="Базовый URL REST API"
)

st.set_page_config(
    page_title="ML Service Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d1f2eb;
        border: 1px solid #a3e4d7;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        color: #0c5460;
    }
    .info-box {
        background-color: #d6eaf8;
        border: 1px solid #aed6f1;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        color: #154360;
    }
    .stButton>button {
        width: 100%;
        border-radius: 0.5rem;
        background-color: #1f77b4 !important;
        color: white !important;
        border: none !important;
    }
    .stButton>button:hover {
        background-color: #1565a0 !important;
        color: white !important;
    }
    button[kind="primary"] {
        background-color: #1f77b4 !important;
        color: white !important;
    }
    button[kind="primary"]:hover {
        background-color: #1565a0 !important;
    }
    /* Красные кнопки для удаления */
    .stButton > button[kind="secondary"] {
        background-color: #1f77b4 !important;
        color: white !important;
    }
    /* Специальный стиль для кнопок удаления через JavaScript */
</style>
""", unsafe_allow_html=True)


def make_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """
    Выполнить HTTP запрос к API.

    Args:
        method: HTTP метод
        endpoint: Эндпоинт API
        **kwargs: Дополнительные параметры для requests

    Returns:
        Ответ API в виде словаря
    """
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, **kwargs, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return {"error": f"Неподдерживаемый метод: {method}"}

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def check_health() -> bool:
    """Проверить статус API."""
    result = make_request("GET", "/api/v1/health")
    if "error" in result:
        return False
    return result.get("status") == "healthy"


def get_default_hyperparameters(model_type: str) -> Dict[str, Any]:
    """Получить гиперпараметры по умолчанию для модели."""
    defaults = {
        "linear": {
            "alpha": 1.0,
            "max_iter": 1000,
            "tol": 0.0001,
            "solver": "auto"
        },
        "random_forest": {
            "n_estimators": 100,
            "max_depth": None,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "random_state": 42
        }
    }
    return defaults.get(model_type, {})


st.markdown("""
<script>
    // Ждем загрузки DOM
    setTimeout(function() {
        // Находим все кнопки с текстом "🗑️ Удалить"
        const buttons = document.querySelectorAll('button');
        buttons.forEach(function(button) {
            if (button.textContent.includes('🗑️')) {
                button.style.backgroundColor = '#dc3545';
                button.style.color = 'white';
                button.style.borderColor = '#dc3545';
                button.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#c82333';
                });
                button.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = '#dc3545';
                });
            }
        });
    }, 100);
</script>
""", unsafe_allow_html=True)

health_status = check_health()
if not health_status:
    st.error(f"⚠️ Не удалось подключиться к API по адресу {API_BASE_URL}")
    st.info("💡 Попробуйте изменить URL в боковой панели или проверьте что API запущен")

st.sidebar.title("🤖 ML Service Dashboard")
st.sidebar.markdown("---")

page = st.sidebar.selectbox(
    "📋 Выберите раздел",
    ["📊 Датасеты", "🎓 Обучение", "🔮 Инференс"],
    format_func=lambda x: x.split(" ", 1)[1] if " " in x else x
)

if page == "📊 Датасеты":
    st.markdown('<h1 class="main-header">📊 Управление датасетами</h1>', unsafe_allow_html=True)

    st.markdown("### 📤 Загрузка датасета")
    uploaded_file = st.file_uploader(
        "Выберите файл датасета (CSV или JSON)", 
        type=["csv", "json"],
        help="Поддерживаются форматы CSV и JSON"
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns([3, 1])
        with col1:
            format_type = st.selectbox("Формат файла", ["csv", "json"], key="upload_format")
        with col2:
            st.write("")  # Отступ
            st.write("")  # Отступ
            if st.button("📥 Загрузить", type="primary", use_container_width=True):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {"format": format_type}
                result = make_request(
                    "POST", "/api/v1/datasets/upload", files=files, data=data
                )
                if "error" in result:
                    st.error(f"❌ Ошибка: {result['error']}")
                else:
                    st.success(f"✅ Датасет {result.get('file_name', result.get('filename', 'Unknown'))} успешно загружен!")
                    st.markdown(f'<div class="success-box">📦 <strong>ID:</strong> {result["dataset_id"]}<br>📏 <strong>Размер:</strong> {result["size"]} байт</div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 📋 Список датасетов")
    if st.button("🔄 Обновить список", use_container_width=True):
        st.rerun()

    datasets_result = make_request("GET", "/api/v1/datasets")
    if "error" in datasets_result:
        st.error(f"❌ Ошибка при получении списка датасетов: {datasets_result['error']}")
    else:
        datasets = datasets_result if isinstance(datasets_result, list) else []
        if datasets:
            for dataset in datasets:
                with st.expander(
                    f"📊 {dataset.get('file_name', dataset.get('filename', 'Unknown'))} (ID: {dataset['dataset_id'][:8]}...)"
                ):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📏 Размер", f"{dataset['size']:,} байт")
                    with col2:
                        st.metric("📅 Создан", dataset['created_at'][:10])
                    with col3:
                        if dataset.get("dvc_version"):
                            st.metric("🔖 DVC версия", dataset['dvc_version'][:8] + "...")
                        else:
                            st.metric("🔖 DVC версия", "N/A")

                    if st.button(
                        "🗑️ Удалить", 
                        key=f"delete_{dataset['dataset_id']}",
                        use_container_width=True
                    ):
                        result = make_request(
                            "DELETE", f"/api/v1/datasets/{dataset['dataset_id']}"
                        )
                        if "error" in result:
                            st.error(f"❌ Ошибка: {result['error']}")
                        else:
                            st.success("✅ Датасет удален!")
                            st.rerun()
        else:
            st.info("ℹ️ Нет загруженных датасетов. Загрузите первый датасет выше.")

elif page == "🎓 Обучение":
    st.markdown('<h1 class="main-header">🎓 Обучение моделей</h1>', unsafe_allow_html=True)

    models_result = make_request("GET", "/api/v1/models/available")
    if "error" in models_result:
        st.error(f"❌ Ошибка: {models_result['error']}")
        st.stop()

    available_models = models_result if isinstance(models_result, list) else []

    datasets_result = make_request("GET", "/api/v1/datasets")
    datasets = (
        datasets_result if isinstance(datasets_result, list) and "error" not in datasets_result else []
    )

    if not datasets:
        st.warning("⚠️ Сначала загрузите датасет в разделе '📊 Датасеты'")
        st.stop()

    st.markdown("### ⚙️ Настройка обучения")

    col1, col2 = st.columns(2)
    with col1:
        model_type = st.selectbox("🤖 Тип модели", available_models)
    with col2:
        dataset_options = {
            f"{d.get('file_name', d.get('filename', 'Unknown'))} ({d['dataset_id'][:8]}...)": d["dataset_id"]
            for d in datasets
        }
        selected_dataset = st.selectbox("📊 Датасет", list(dataset_options.keys()))
        dataset_id = dataset_options[selected_dataset]

    st.markdown("### 🎛️ Гиперпараметры")
    
    default_params = get_default_hyperparameters(model_type)
    st.info(f"💡 **Подсказка:** Для модели **{model_type}** доступны параметры: {', '.join(default_params.keys())}")
    
    if st.button("📋 Загрузить параметры по умолчанию", use_container_width=True):
        st.session_state.default_hyperparams = json.dumps(default_params, indent=2)
    
    hyperparameters_json = st.text_area(
        "JSON с гиперпараметрами",
        value=st.session_state.get("default_hyperparams", json.dumps(default_params, indent=2)),
        height=200,
        help=f'Пример для {model_type}: {json.dumps(default_params, indent=2)}',
    )

    try:
        hyperparameters = json.loads(hyperparameters_json)
    except json.JSONDecodeError as e:
        st.error(f"❌ Неверный формат JSON: {e}")
        hyperparameters = default_params

    if st.button("🚀 Обучить модель", type="primary", use_container_width=True):
        with st.spinner("⏳ Обучение модели... Это может занять некоторое время."):
            result = make_request(
                "POST",
                "/api/v1/models/train",
                json={
                    "model_type": model_type,
                    "dataset_id": dataset_id,
                    "hyperparameters": hyperparameters,
                },
            )

            if "error" in result:
                st.error(f"❌ Ошибка при обучении: {result['error']}")
            else:
                st.success("✅ Модель успешно обучена!")
                
                if result.get("metrics"):
                    st.markdown("### 📊 Метрики модели")
                    metrics = result["metrics"]
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("R² Score", f"{metrics.get('r2_score', 0):.4f}")
                    with col2:
                        st.metric("MAE", f"{metrics.get('mae', 0):.4f}")
                    with col3:
                        st.metric("MSE", f"{metrics.get('mse', 0):.4f}")
                    with col4:
                        st.metric("RMSE", f"{metrics.get('rmse', 0):.4f}")
                
                st.markdown(f'<div class="success-box"><strong>📦 ID модели:</strong> {result["model_id"]}</div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 📋 Обученные модели")
    if st.button("🔄 Обновить список моделей", use_container_width=True):
        st.rerun()

    models_result = make_request("GET", "/api/v1/models")
    if "error" in models_result:
        st.error(f"❌ Ошибка: {models_result['error']}")
    else:
        models = models_result if isinstance(models_result, list) else []
        if models:
            for model in models:
                with st.expander(
                    f"🤖 {model['model_type']} (ID: {model['model_id'][:8]}...)"
                ):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📊 Статус", model['status'])
                    with col2:
                        st.metric("📦 Датасет", model['dataset_id'][:8] + "...")
                    with col3:
                        st.metric("📅 Создана", model['created_at'][:10])

                    if model.get("metrics"):
                        st.markdown("**📊 Метрики:**")
                        metrics = model["metrics"]
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("R²", f"{metrics.get('r2_score', 0):.4f}")
                        with col2:
                            st.metric("MAE", f"{metrics.get('mae', 0):.4f}")
                        with col3:
                            st.metric("MSE", f"{metrics.get('mse', 0):.4f}")
                        with col4:
                            st.metric("RMSE", f"{metrics.get('rmse', 0):.4f}")

                    st.markdown("**⚙️ Гиперпараметры:**")
                    st.json(model["hyperparameters"])

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "🔄 Переобучить", 
                            key=f"retrain_{model['model_id']}",
                            use_container_width=True
                        ):
                            st.info("💡 Используйте форму выше для переобучения")
                    with col2:
                        delete_model_btn = st.button(
                            "🗑️ Удалить", 
                            key=f"delete_model_{model['model_id']}",
                            use_container_width=True,
                            type="secondary"
                        )
                        if delete_model_btn:
                            result = make_request(
                                "DELETE", f"/api/v1/models/{model['model_id']}"
                            )
                            if "error" in result:
                                st.error(f"❌ Ошибка: {result['error']}")
                            else:
                                st.success("✅ Модель удалена!")
                                st.rerun()
        else:
            st.info("ℹ️ Нет обученных моделей. Обучите первую модель выше.")

# Страница: Инференс
elif page == "🔮 Инференс":
    st.markdown('<h1 class="main-header">🔮 Получение предсказаний</h1>', unsafe_allow_html=True)

    models_result = make_request("GET", "/api/v1/models")
    if "error" in models_result:
        st.error(f"❌ Ошибка: {models_result['error']}")
        st.stop()

    models = models_result if isinstance(models_result, list) else []
    if not models:
        st.warning("⚠️ Сначала обучите модель в разделе '🎓 Обучение'")
        st.stop()

    model_options = {
        f"{m['model_type']} ({m['model_id'][:8]}...)": m["model_id"]
        for m in models
    }
    selected_model = st.selectbox("🤖 Выберите модель", list(model_options.keys()))
    model_id = model_options[selected_model]

    st.markdown("---")

    st.markdown("### 📥 Ввод признаков")

    input_method = st.radio(
        "Способ ввода",
        ["✍️ Ручной ввод", "📄 Загрузка CSV", "📄 Загрузка JSON", "📝 Ввод JSON текстом"],
        horizontal=True
    )

    features = None

    if input_method == "✍️ Ручной ввод":
        num_features = st.number_input(
            "Количество признаков", min_value=1, max_value=100, value=3
        )
        num_samples = st.number_input(
            "Количество образцов", min_value=1, max_value=100, value=1
        )

        features = []
        for i in range(num_samples):
            st.write(f"**Образец {i + 1}:**")
            sample_features = []
            cols = st.columns(num_features)
            for j, col in enumerate(cols):
                with col:
                    value = st.number_input(
                        f"Признак {j + 1}",
                        key=f"feature_{i}_{j}",
                        value=0.0,
                        step=0.1,
                    )
                    sample_features.append(value)
            features.append(sample_features)

    elif input_method == "📄 Загрузка CSV":
        uploaded_file = st.file_uploader(
            "Загрузите CSV файл с признаками", type=["csv"]
        )
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write("**📊 Предпросмотр данных:**")
            st.dataframe(df.head())
            features = df.values.tolist()

    elif input_method == "📄 Загрузка JSON":
        uploaded_file = st.file_uploader(
            "Загрузите JSON файл с признаками", type=["json"]
        )
        if uploaded_file is not None:
            data = json.load(uploaded_file)
            if isinstance(data, list):
                if len(data) == 0:
                    st.error("❌ JSON файл пуст")
                    features = None
                elif isinstance(data[0], list):
                    features = data
                elif isinstance(data[0], dict):
                    features = data
                    st.success(f"✅ Загружено {len(features)} образцов с именованными полями")
                    if features:
                        st.json({"Пример первого образца": features[0]})
            elif isinstance(data, dict) and "features" in data:
                features = data["features"]
            else:
                st.error("❌ Неверный формат JSON. Ожидается массив массивов, массив объектов или объект с полем 'features'")
                features = None

    elif input_method == "📝 Ввод JSON текстом":
        json_text = st.text_area(
            "Введите JSON с признаками",
            height=300,
            help='Пример списка списков: [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]\nПример списка объектов: [{"alcohol": 14.23, "malic_acid": 1.71, ...}, ...]',
            value='[\n  {\n    "alcohol": 14.23,\n    "malic_acid": 1.71,\n    "ash": 2.43\n  }\n]'
        )
        if json_text:
            try:
                data = json.loads(json_text)
                if isinstance(data, list):
                    if len(data) == 0:
                        st.error("❌ JSON пуст")
                        features = None
                    elif isinstance(data[0], list):
                        features = data
                        st.success(f"✅ Загружено {len(features)} образцов")
                    elif isinstance(data[0], dict):
                        features = data
                        st.success(f"✅ Загружено {len(features)} образцов с именованными полями")
                        if features:
                            st.json({"Пример первого образца": features[0]})
                    else:
                        st.error("❌ Неверный формат: элементы должны быть списками или объектами")
                        features = None
                elif isinstance(data, dict) and "features" in data:
                    features = data["features"]
                else:
                    st.error("❌ Неверный формат JSON")
                    features = None
            except json.JSONDecodeError as e:
                st.error(f"❌ Ошибка парсинга JSON: {e}")
                features = None

    if features and st.button("🔮 Получить предсказания", type="primary", use_container_width=True):
        with st.spinner("⏳ Вычисление предсказаний..."):
            result = make_request(
                "POST",
                f"/api/v1/models/{model_id}/predict",
                json={"features": features},
            )

            if "error" in result:
                st.error(f"❌ Ошибка: {result['error']}")
            else:
                st.success("✅ Предсказания получены!")
                st.markdown("### 📊 Результаты")
                
                results_df = pd.DataFrame({
                    "Образец": [f"#{i+1}" for i in range(len(result["predictions"]))],
                    "Предсказание": result["predictions"],
                })
                
                st.dataframe(results_df, use_container_width=True)
                
                if len(result["predictions"]) > 1:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📊 Количество", len(result["predictions"]))
                    with col2:
                        st.metric("📈 Среднее", f"{sum(result['predictions'])/len(result['predictions']):.4f}")
                    with col3:
                        st.metric("📉 Мин/Макс", f"{min(result['predictions']):.4f} / {max(result['predictions']):.4f}")
                
                if len(result["predictions"]) > 1:
                    st.markdown("### 📈 Визуализация")
                    st.bar_chart(results_df.set_index("Образец"))
                else:
                    st.markdown(f'<div class="info-box"><strong>🔮 Предсказание:</strong> {result["predictions"][0]:.4f}</div>', unsafe_allow_html=True)
