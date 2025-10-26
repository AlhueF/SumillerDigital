import streamlit as st
import pandas as pd
import numpy as np
import pymongo
from typing import Dict, List, Tuple, Optional
import logging
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar Gemini API
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Configuración de la página
st.set_page_config(
    page_title="🍷 Maridaje Perfecto",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WineRecommendationApp:
    def __init__(self):
        self.df_vinos = None
        self.df_platos = None
        self.mongo_client = None
        self.wine_types = []  # Se llenará cuando se carguen los datos
        
    @st.cache_data
    def load_wine_data(_self) -> pd.DataFrame:
        """Carga el dataset de vinos desde CSV"""
        try:
            df = pd.read_csv('./data/vinos.csv')
            
            if 'type' in df.columns:
                df['type'] = df['type'].str.lower()
            logger.info(f"Dataset de vinos cargado: {len(df)} registros")
            return df
        except FileNotFoundError:
            st.error("❌ No se encontró el archivo './data/vinos.csv'")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"❌ Error al cargar el dataset de vinos: {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data
    def load_platos_from_mongodb(_self, connection_string: str = "mongodb://localhost:27017/") -> pd.DataFrame:
        """Carga los platos desde MongoDB"""
        try:
            client = pymongo.MongoClient(connection_string)
            db = client['menu_database']  # Cambiado a menu_database
            collection = db['platos']
            
            # Obtener todos los documentos
            platos_data = list(collection.find())
            
            if not platos_data:
                st.warning("⚠️ No se encontraron platos en la base de datos MongoDB")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(platos_data)
            
            # Eliminar el campo _id si existe
            if '_id' in df.columns:
                df = df.drop('_id', axis=1)
            
            logger.info(f"Platos cargados desde MongoDB: {len(df)} registros")
            return df
            
        except Exception as e:
            st.error(f"❌ Error al conectar con MongoDB: {str(e)}")
            return pd.DataFrame()
    
    def get_categories(self, df_platos: pd.DataFrame) -> List[str]:
        """Obtiene las categorías únicas de platos"""
        if df_platos.empty or 'categoria' not in df_platos.columns:
            return []
        return sorted(df_platos['categoria'].unique().tolist())
    
    def get_platos_by_category(self, df_platos: pd.DataFrame, categoria: str) -> List[str]:
        """Obtiene los platos de una categoría específica"""
        if df_platos.empty or 'nombre_plato' not in df_platos.columns:
            return []
        platos_filtrados = df_platos[df_platos['categoria'] == categoria]
        return sorted(platos_filtrados['nombre_plato'].unique().tolist())
    
    def get_plato_properties(self, df_platos: pd.DataFrame, nombre_plato: str) -> Tuple[float, float, List[str]]:
        """Obtiene las propiedades de acidez, cuerpo y maridajes recomendados de un plato"""
        plato_data = df_platos[df_platos['nombre_plato'] == nombre_plato]
        if plato_data.empty:
            return 0.0, 0.0, []
        
        # Convertir a float y manejar el caso donde termina en punto
        def clean_number(val):
            if isinstance(val, str):
                return float(val.rstrip('.'))
            return float(val)
        
        acidity = clean_number(plato_data.iloc[0]['acidez']) if 'acidez' in plato_data.columns else 0.0
        body = clean_number(plato_data.iloc[0]['cuerpo']) if 'cuerpo' in plato_data.columns else 0.0
        
        # Obtener maridajes recomendados
        maridajes = plato_data.iloc[0].get('maridaje', [])
        if isinstance(maridajes, str):
            # Si es una cadena, convertir a lista y limpiar
            maridajes = [m.strip().lower() for m in maridajes.split(',')]
        elif not isinstance(maridajes, list):
            maridajes = []
        
        return acidity, body, maridajes
    
    def filter_wines_by_similarity(self, df_vinos: pd.DataFrame, target_acidity: float, 
                                 target_body: float, wine_type: str, 
                                 recommended_types: List[str], tolerance: float = 0.4) -> pd.DataFrame:
        """Filtra vinos por similitud en acidez y cuerpo, considerando los maridajes recomendados
        
        Los valores de acidez y cuerpo deben estar normalizados entre 0 y 1.
        La tolerancia por defecto es 0.4 para permitir encontrar valores aproximados.
        """
        # Verificar si el tipo de vino está en los maridajes recomendados
        if wine_type.lower() not in [t.lower() for t in recommended_types]:
            return pd.DataFrame()
            
        # Filtrar por tipo de vino
        df_filtered = df_vinos[df_vinos['type'].str.lower() == wine_type.lower()].copy()
        
        if df_filtered.empty:
            return df_filtered
            
        # Asegurar que los valores estén entre 0 y 1
        target_acidity = np.clip(target_acidity / 5.0, 0, 1)
        target_body = np.clip(target_body / 5.0, 0, 1)
        
        # Normalizar valores del DataFrame
        df_filtered['acidity_norm'] = df_filtered['acidity'] / 5.0
        df_filtered['body_norm'] = df_filtered['body'] / 5.0
            
        # Calcular distancia euclidiana normalizada para similitud
        df_filtered['distance'] = np.sqrt(
            (df_filtered['acidity_norm'] - target_acidity) ** 2 + 
            (df_filtered['body_norm'] - target_body) ** 2
        )
        
        # La distancia máxima posible en un espacio normalizado 2D es √2 ≈ 1.414
        # Ajustamos la tolerancia para encontrar más coincidencias si es necesario
        if df_filtered[df_filtered['distance'] <= tolerance].empty:
            # Si no hay coincidencias, aumentamos gradualmente la tolerancia
            tolerance = min(tolerance * 1.5, 0.8)  # máximo 0.8 para evitar coincidencias muy lejanas
        
        # Filtrar por tolerancia y ordenar por distancia
        df_filtered = df_filtered[df_filtered['distance'] <= tolerance]
        df_filtered = df_filtered.sort_values('distance')
        
        # Eliminar columnas temporales de normalización
        df_filtered = df_filtered.drop(['acidity_norm', 'body_norm'], axis=1)
        
        return df_filtered
    
    def divide_wines_by_price_ranges(self, df_wines: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Divide los vinos en tres rangos de precio (tercios)"""
        if df_wines.empty:
            return {"Económico": pd.DataFrame(), "Intermedio": pd.DataFrame(), "Premium": pd.DataFrame()}
        
        # Calcular percentiles
        p33 = df_wines['price'].quantile(0.33)
        p66 = df_wines['price'].quantile(0.66)
        
        economico = df_wines[df_wines['price'] <= p33]
        intermedio = df_wines[(df_wines['price'] > p33) & (df_wines['price'] <= p66)]
        premium = df_wines[df_wines['price'] > p66]
        
        return {
            "Económico": economico,
            "Intermedio": intermedio,
            "Premium": premium
        }
    
    def select_best_wine_in_range(self, df_range: pd.DataFrame) -> Optional[pd.Series]:
        """Selecciona el mejor vino en un rango de precio basado en rating y reviews"""
        if df_range.empty:
            return None
        
        # Calcular score combinando rating y número de reviews
        df_temp = df_range.copy()
        df_temp['score'] = df_temp['rating'] * np.log(df_temp['num_reviews'] + 1)
        
        # Seleccionar el vino con mejor score
        best_wine = df_temp.loc[df_temp['score'].idxmax()]
        return best_wine
    
    def recommend_wines(self, df_vinos: pd.DataFrame, target_acidity: float, 
                       target_body: float, recommended_types: List[str]) -> pd.DataFrame:
        """Recomienda vinos basándose en los maridajes sugeridos para el plato y 
        la similitud de acidez y cuerpo"""
        recommendations = []
        
        # Filtrar wine_types para incluir solo los tipos recomendados
        valid_types = [t for t in self.wine_types if t.lower() in [rt.lower() for rt in recommended_types]]
        
        for wine_type in valid_types:
            # Filtrar vinos por tipo y similitud
            filtered_wines = self.filter_wines_by_similarity(
                df_vinos, target_acidity, target_body, wine_type, recommended_types
            )
            
            if filtered_wines.empty:
                continue
            
            # Dividir en rangos de precio
            price_ranges = self.divide_wines_by_price_ranges(filtered_wines)
            
            # Seleccionar mejor vino de cada rango
            for range_name, df_range in price_ranges.items():
                best_wine = self.select_best_wine_in_range(df_range)
                if best_wine is not None:
                    wine_data = best_wine.to_dict()
                    wine_data['price_range'] = range_name
                    wine_data['wine_type_category'] = wine_type.capitalize()
                    recommendations.append(wine_data)
        
        return pd.DataFrame(recommendations)
    
    def generate_poetic_recommendation(self, wine_data: Dict, plato_name: str, plato_data: Dict) -> str:
        """Genera una recomendación poética y narrativa del maridaje usando Gemini API"""
        try:
            # Preparar los datos para el prompt
            wine_info = {
                "nombre": wine_data.get('wine', 'Vino seleccionado'),
                "bodega": wine_data.get('winery', ''),
                "año": wine_data.get('year', ''),
                "tipo": wine_data.get('type', '').lower(),
                "país": wine_data.get('country', ''),
                "región": wine_data.get('region', ''),
                "acidez": wine_data.get('acidity', 0),
                "cuerpo": wine_data.get('body', 0)
            }

            plato_info = {
                "nombre": plato_name,
                "descripción": plato_data.get('descripcion', ''),
                "acidez": plato_data.get('acidez', 0),
                "cuerpo": plato_data.get('cuerpo', 0),
                "ingredientes": plato_data.get('ingredientes_clave', [])
            }

            # Crear el prompt para Gemini
            prompt = f"""
            Eres un sommelier experto en maridajes. Genera una descripción profesional y clara del 
            maridaje entre un vino y un plato. Usa un lenguaje elegante y preciso, evitando tanto 
            tecnicismos excesivos como expresiones demasiado poéticas o metafóricas.

            VINO:
            - Nombre: {wine_info['nombre']}
            - Bodega: {wine_info['bodega']}
            - Año: {wine_info['año']}
            - Tipo: {wine_info['tipo']}
            - Región: {wine_info['región']}, {wine_info['país']}
            - Acidez: {wine_info['acidez']}/5
            - Cuerpo: {wine_info['cuerpo']}/5

            PLATO:
            - Nombre: {plato_info['nombre']}
            - Descripción: {plato_info['descripción']}
            - Acidez: {plato_info['acidez']}/5
            - Cuerpo: {plato_info['cuerpo']}/5
            - Ingredientes clave: {', '.join(plato_info['ingredientes'])}

            Por favor, genera una recomendación que incluya:
            1. Un título descriptivo y elegante
            2. Una explicación clara del equilibrio entre el vino y el plato
            3. Una descripción precisa de aromas y texturas
            4. Recomendaciones prácticas de servicio y temperatura
            5. Una breve conclusión sobre la experiencia de maridaje

            El formato debe ser en Markdown e incluir emojis apropiados.
            Usa un tono profesional y accesible, como un experto compartiendo su conocimiento 
            de manera clara y directa. Evita metáforas elaboradas o lenguaje demasiado florido.
            
            La descripción debe enfocarse en aspectos tangibles y prácticos del maridaje, 
            destacando características específicas que hacen que esta combinación funcione bien.
            """

            # Llamar a Gemini API
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            
            # Procesar y devolver la respuesta
            if response.text:
                return response.text
            else:
                raise Exception("No se generó respuesta")

        except Exception as e:
            logger.error(f"Error generando recomendación: {str(e)}")
            return self._generate_fallback_recommendation(wine_data, plato_name)

    def _generate_fallback_recommendation(self, wine_data: Dict, plato_name: str) -> str:
        """Genera una recomendación básica en caso de error con la API"""
        return f"""
        ### 🍷 Recomendación de Maridaje
        
        ---
        
        **{wine_data.get('wine', 'Vino seleccionado')}** 
        *{wine_data.get('winery', '')} ({wine_data.get('year', '')})*
        
        Esta combinación de vino y **{plato_name}** ofrece un equilibrio de sabores 
        y texturas que complementan las características de ambos elementos.
        
        ---
        """
        

    
    def run(self):
        """Función principal de la aplicación"""
        # Título principal
        st.title("🍷 Maridaje Perfecto")
        st.markdown("### *Descubre el vino ideal para tu plato favorito*")
        st.markdown("---")
        
        # Sidebar para configuración
        with st.sidebar:
            st.header("⚙️ Configuración")
            mongo_connection = st.text_input(
                "Conexión MongoDB", 
                value="mongodb://localhost:27017/",
                help="Cadena de conexión a MongoDB"
            )
            
            if st.button("🔄 Recargar Datos"):
                st.cache_data.clear()
                st.rerun()
        
        # Cargar datos
        with st.spinner("Cargando datos..."):
            self.df_vinos = self.load_wine_data()
            self.df_platos = self.load_platos_from_mongodb(mongo_connection)
            
            # Actualizar lista de tipos de vino
            if not self.df_vinos.empty and 'type' in self.df_vinos.columns:
                self.wine_types = sorted(self.df_vinos['type'].unique().tolist())
        
        # Verificar que los datos se cargaron correctamente
        if self.df_vinos.empty:
            st.error("❌ No se pudieron cargar los datos de vinos")
            return
        
        if self.df_platos.empty:
            st.error("❌ No se pudieron cargar los datos de platos")
            return
        
        # Mostrar estadísticas básicas
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🍷 Vinos disponibles", len(self.df_vinos))
        with col2:
            st.metric("🍽️ Platos disponibles", len(self.df_platos))
        
        st.markdown("---")
        
        # Paso 2: Selección de platos
        st.header("1️⃣ Selecciona tu plato")
        
        categories = self.get_categories(self.df_platos)
        
        if not categories:
            st.error("❌ No se encontraron categorías de platos")
            return
        
        # Selección de categoría
        selected_category = st.selectbox(
            "🏷️ Elige una categoría:",
            categories,
            index=0
        )
        
        # Selección de plato
        platos_in_category = self.get_platos_by_category(self.df_platos, selected_category)
        
        if not platos_in_category:
            st.warning(f"⚠️ No se encontraron platos en la categoría '{selected_category}'")
            return
        
        selected_plato = st.selectbox(
            "🍽️ Elige tu plato:",
            platos_in_category,
            index=0
        )
        
        # Obtener propiedades del plato
        plato_acidity, plato_body, recommended_types = self.get_plato_properties(self.df_platos, selected_plato)
        
        # Mostrar propiedades del plato
        st.info(f"**Plato seleccionado:** {selected_plato}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🍋 Acidez", f"{plato_acidity:.2f}")
        with col2:
            st.metric("💪 Cuerpo", f"{plato_body:.2f}")
            
        # Mostrar tipos de vino recomendados
        if recommended_types:
            st.info(f"🍷 **Tipos de vino recomendados:** {', '.join(recommended_types)}")
        
        st.markdown("---")
        
        # Paso 3: Recomendación de vinos
        st.header("2️⃣ Vinos recomendados")
        
        with st.spinner("Analizando maridajes..."):
            recommended_wines = self.recommend_wines(self.df_vinos, plato_acidity, plato_body, recommended_types)
        
        if recommended_wines.empty:
            st.warning("⚠️ No se encontraron vinos compatibles con este plato")
            return
        
        # Mostrar vinos recomendados
        st.subheader("🎯 Los mejores maridajes para tu plato")
        
        # Crear opciones para el radio button
        wine_options = []
        for idx, wine in recommended_wines.iterrows():
            option_text = f"{wine['wine']} - {wine['winery']} ({wine['wine_type_category']}, {wine['price_range']}) - ${wine['price']:.2f}"
            wine_options.append(option_text)
        
        # Mostrar tabla de vinos
        display_columns = ['wine', 'winery', 'type', 'price', 'rating', 'num_reviews', 
                          'country', 'region', 'year', 'price_range']
        
        available_columns = [col for col in display_columns if col in recommended_wines.columns]
        st.dataframe(recommended_wines[available_columns], use_container_width=True)
        
        st.markdown("---")
        
        # Paso 4: Selección final
        st.header("3️⃣ Tu elección final")
        
        if wine_options:
            selected_wine_idx = st.radio(
                "🎯 Selecciona tu vino favorito:",
                range(len(wine_options)),
                format_func=lambda x: wine_options[x]
            )
            
            # Obtener el vino seleccionado
            selected_wine_data = recommended_wines.iloc[selected_wine_idx].to_dict()
            
            st.markdown("---")
            
            # Paso 5: Recomendación poética
            st.header("4️⃣ Tu maridaje perfecto")
            
            # Obtener datos completos del plato
            plato_data = self.df_platos[self.df_platos['nombre_plato'] == selected_plato].iloc[0].to_dict()
            
            poetic_recommendation = self.generate_poetic_recommendation(
                selected_wine_data, selected_plato, plato_data
            )
            
            st.markdown(poetic_recommendation)
            
            # Información adicional del vino seleccionado
            with st.expander("📊 Detalles técnicos del vino"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⭐ Rating", f"{selected_wine_data.get('rating', 0):.1f}")
                with col2:
                    st.metric("💬 Reviews", f"{selected_wine_data.get('num_reviews', 0):,}")
                with col3:
                    st.metric("💰 Precio", f"${selected_wine_data.get('price', 0):.2f}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("🍋 Acidez del vino", f"{selected_wine_data.get('acidity', 0):.2f}")
                with col2:
                    st.metric("💪 Cuerpo del vino", f"{selected_wine_data.get('body', 0):.2f}")

# Punto de entrada de la aplicación
if __name__ == "__main__":
    app = WineRecommendationApp()
    app.run()