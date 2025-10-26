# Sistema Híbrido de Recomendación de Maridajes (Sumiller Digital)
## ## 📁 Recursos del Proyecto
[Acceder a la Carpeta de Recursos de Google Drive]([https://drive.google.com/drive/folders/1l7mlE7hbvi--737cqKSFdDe2AK90Whbu?usp=sharing])
## Objetivo principal

Diseñar, desarrollar y evaluar un Sistema de Recomendación de Maridajes (MVP) que integre reglas expertas y características del vino, accesible mediante una web móvil que funcione como “Sumiller Digital”. 

## Objetivos específicos

Desarrollar un algoritmo de Ranking para calcular la similitud entre los perfiles organolépticos (acidez, cuerpo) del plato y del vino.
Integrar un modelo de Inteligencia Artificial Generativa (LLM), específicamente la API de Google Gemini, para transformar el resultado del ranking técnico en una justificación narrativa y conversacional del maridaje.

Proporcionar al comensal rápidamente información sobre la combinación idónea de vinos de diferentes presupuestos de acuerdo al plato que desee ordenar.

Reducir la dependencia de personal especializado.

Incrementar el promedio de ticket (ticket medio) del restaurante.

## Inicialización y Adquisición de Datos

### Menú
Se extrae el texto de los platos del menú.
Se hace un diccionario para cada plato incluyendo: nombre del plato, categoría (principal, entrante, postre), ingredientes clave, carne (Si/No), proteina principal.  Se hace una consulta a gemini-2.5-flash para que genere esos diccionarios. Se almacenan en MongoDB.

### Dataset vinos
Se carga el dataset “wine_SPA.csv”(https://www.kaggle.com/datasets/fedesoriano/spanish-wine-quality-dataset).
Está compuesto por 7.500 filas y 11 columnas.
Cada fila corresponde a un vino.
Cada columna corresponde a una característica de ese vino. Se incluyen datos sobre el nombre del vino, la bodega de la cual proviene, el año de la cosecha, la calificación promedio obtenida en las reseñas, el número de reseñas sobre el vino, el país de origen (todos provienen de España), la región del vino, el precio en euros, la variedad, la puntuación de cuerpo y la puntuación de acidez.

Tiene:
6 campos tipo "object": winery, wine, year, country, region, type.
4 campos tipo "floats": rating, price, body, acidity
1 campo tipo "int": num_reviews

## Limpieza y procesamiento de los datos

 Se realiza un análisis exploratorio para limpiar el dataset.
Se visualizan las filas que tienen valores Nan en type, body y acidit. (en las tres columnas). Se procede a eliminar dichas filas ya que estas columnas contienen los datos relevantes para el maridaje.

  Se normalizan las columnas “acidity” y “body”estableciendo valores del 0 al 1.

  Ya que todos los vinos son españoles se elimina la columna “country”.

  Se guarda el nuevo dataset limpio “vinos.csv”.

  Se carga en memoria con Pandas y se optimiza su acceso mediante el mecanismo de cache de Streamlit para asegurar una respuesta rápida en subsecuentes consultas.

  Los datos de los platos del menú se adquieren desde la base de datos MongoDB a través del driver PyMongo. 

  Luego de limpiar y preparar los datos de vinos y del menú sigue la Configuración del LLM. La API de Google Gemini se configura utilizando claves de entorno (os.getenv), preparando el sistema para las consultas de generación de lenguaje.


## Arquitectura de Software y Entorno

El MVP opera bajo una arquitectura de microservicio orientada a datos, con el siguiente stack tecnológico:

Backend y Lógica: Python es el lenguaje principal. La gestión del entorno se realiza con variables de entorno (dotenv) y el logging con la librería logging.

Base de Datos de Menú: MongoDB (conectado vía pymongo a mongodb://localhost:27017/menu_database). Permite que el sistema sea modular, separando los datos del menú de los datos estáticos de vinos.

Frontend y Deploy: Streamlit (import streamlit as st) crea la aplicación web móvil interactiva y responsive, aprovechando @st.cache_data para optimizar la carga inicial y el rendimiento.

## Algoritmo de Recomendación por Similitud Organoléptica

  El proceso central de recomendación se articula mediante una función de ranking que opera en tres fases:

### Filtro Primario (Reglas Expertas):

La aplicación consulta las “recommended types” almacenadas en MongoDB para el plato seleccionado. Solo los vinos que coinciden con estos tipos predefinidos pasan a la siguiente fase.

### Cálculo de Similitud (Distancia Euclidiana):

Para los vinos filtrados, el sistema calcula la Distancia Euclidiana Normalizada entre el perfil organoléptico objetivo del plato (acidez y cuerpo deseados) y el perfil real del vino. Esto garantiza la coherencia técnica del maridaje.

Se aplica una tolerancia inicial (tolerance = 0.4) para limitar las coincidencias, con un mecanismo de fallback que amplía la tolerancia (tolerance * 1.5, máximo 0.8) si no se encuentran vinos que cumplan el criterio de coherencia estricta.

### Ranking y Segmentación por Precio: 

Los vinos coherentes se segmentan en rangos de precio (Económico, Intermedio, Premium) utilizando cuartiles para definir los umbrales. Dentro de cada rango, se selecciona el mejor vino utilizando el siguiente score ponderado, que maximiza la calidad percibida (rating) y la confianza estadística.
score = rating x log (num_reviews+1)

### Justificación Conversacional con IA Generativa

Para elevar la experiencia del usuario más allá de una simple lista, el sistema integra la API de Google Gemini (gemini-2.5-flash).

  El modelo transforma los datos técnicos del vino y el plato (acidez, cuerpo, ingredientes) en una justificación narrativa y elegante del maridaje. Esto simula el rol del sommelier, proporcionando al comensal una explicación de alto valor.
  
  La narrativa incluye datos de la región del vino, información sobre el tipo de uva, el año de cosecha.
El comensal no solo recibe los nombres de los vinos sugeridos, sino también fundamentos acerca de por qué sería un buen vino para acompañar su plato.

Si quieres ver 

  Se incluye una función de fallback para garantizar que el comensal siempre reciba una recomendación básica y evitar fallos críticos si la API no está disponible.
