import os
import hashlib
import streamlit as st
import pandas as pd
import math
from PIL import Image
import requests
from io import BytesIO

# Путь к папке для хранения изображений
IMAGE_CACHE_DIR = "image_cache"

# Функция для создания уникального имени файла на основе URL
def get_image_filename(url):
    hash_object = hashlib.md5(url.encode())
    return hash_object.hexdigest() + ".png"

# Функция для загрузки изображения из кеша или с URL
def load_image_from_cache_or_url(url, idx):
    if f'image_{idx}' not in st.session_state:
        try:
            # Проверяем, существует ли файл в локальном кеше
            if not os.path.exists(IMAGE_CACHE_DIR):
                os.makedirs(IMAGE_CACHE_DIR)

            image_filename = os.path.join(IMAGE_CACHE_DIR, get_image_filename(url))

            # Если файл существует, загружаем его из кеша
            if os.path.exists(image_filename):
                img = Image.open(image_filename)
                img.load()
                st.session_state[f'image_{idx}'] = (img, os.path.getsize(image_filename))
            else:
                # Если файла нет, загружаем изображение с URL и сохраняем в кеш
                response = requests.get(url)
                img = Image.open(BytesIO(response.content))
                img.save(image_filename)  # Сохраняем изображение в кеш
                img.load()
                st.session_state[f'image_{idx}'] = (img, response.headers.get('Content-Length', None))
        except Exception:
            st.session_state[f'image_{idx}'] = (None, None)
    return st.session_state[f'image_{idx}']

# Функция для отображения данных постранично и изменения порядка изображений
def display_data(df, image_columns, start, end):
    for i in range(start, end):
        row = df.iloc[i]

        if 'Код артикула' in df.columns:
            artikul_value = row['Код артикула']
            st.write(f"Строка {i + 1} — Артикул: {artikul_value if artikul_value else 'Нет значения'}")
        else:
            st.write(f"Строка {i + 1} — Артикул: Столбец 'Код артикула' не найден!")

        # Извлекаем изображения из пронумерованных столбцов
        images = [row[col] for col in image_columns if pd.notna(row[col])]

        # Создаем порядок изображений для каждой строки в session_state
        if f'order_{i}' not in st.session_state:
            st.session_state[f'order_{i}'] = list(range(len(images)))

        # Пересчитываем порядок после удаления изображений
        st.session_state[f'order_{i}'] = [img_idx for img_idx in st.session_state[f'order_{i}'] if img_idx < len(images)]

        if images:
            scroll_container = st.container()
            with scroll_container:
                cols = st.columns(min(10, len(images)))
                for idx, img_idx in enumerate(st.session_state[f'order_{i}']):
                    with cols[idx % 10]:
                        img_url = images[img_idx]
                        unique_key = f'{i}_{img_idx}_{idx}'
                        img, img_size = load_image_from_cache_or_url(img_url, unique_key)
                        if img:
                            st.image(img, width=100)
                        else:
                            st.markdown(f"""
                                <div style='width:100px;height:100px;background-color:grey;display:flex;align-items:center;justify-content:center;color:white;flex-direction:column;'>
                                    <span>bad link</span>
                                    <a href='{img_url}' target='_blank' style='color:white; text-decoration:none;'>🔗</a>
                                </div>
                            """, unsafe_allow_html=True)

                        # Кнопки для изменения порядка и удаления изображений
                        with st.container():
                            if st.button(f'❌', key=f'delete_{unique_key}'):
                                st.session_state[f'order_{i}'].remove(img_idx)
                                df.at[i, image_columns[img_idx]] = None

                            if idx > 0:
                                if st.button(f'⬅️', key=f'to_start_{unique_key}'):
                                    st.session_state[f'order_{i}'].insert(0, st.session_state[f'order_{i}'].pop(idx))

                            if idx < len(st.session_state[f'order_{i}']) - 1:
                                if st.button(f'➡️', key=f'to_end_{unique_key}'):
                                    st.session_state[f'order_{i}'].append(st.session_state[f'order_{i}'].pop(idx))

                reordered_images = [df.loc[i, image_columns[j]] for j in st.session_state[f'order_{i}']]
                for j, col in enumerate(image_columns):
                    if j < len(reordered_images):
                        df.at[i, col] = reordered_images[j]
                    else:
                        df.at[i, col] = None

        st.write("---")

# Основная функция
def main(file_name, rows_per_page=10):
    st.title("Редактирование данных CSV")

    # Загрузка CSV файла из указанного пути
    try:
        df = pd.read_csv(file_name, sep=';', dtype=str)
    except Exception as e:
        st.error(f"Ошибка загрузки файла: {e}")
        return

    st.write("Доступные столбцы в файле:")
    st.write(df.columns.tolist())

    image_columns = [col for col in df.columns if col.startswith('Изображения товаров')]

    total_rows = df.shape[0]
    total_pages = math.ceil(total_rows / rows_per_page)

    if 'page' not in st.session_state:
        st.session_state.page = 1


    # Слайдер для выбора страницы
    if total_pages > 1:
        st.session_state.page = st.slider("Выберите страницу", min_value=1, max_value=total_pages,
                                          value=st.session_state.page)
    else:
        st.session_state.page = 1

    # Ввод номера страницы
    st.session_state.page = st.number_input("Введите номер страницы", min_value=1, max_value=total_pages,
                                                value=st.session_state.page)

    start_row = (st.session_state.page - 1) * rows_per_page
    end_row = min(start_row + rows_per_page, total_rows)

    display_data(df, image_columns, start_row, end_row)

    # Сохранение изменений для всех страниц, а не только для текущей
    if st.button("Сохранить все изменения"):
        try:
            for i in range(total_rows):
                if f'order_{i}' in st.session_state:
                    order = st.session_state[f'order_{i}']
                    reordered_images = [df.loc[i, image_columns[j]] for j in order]

                    for j, col in enumerate(image_columns):
                        if j < len(reordered_images):
                            df.at[i, col] = reordered_images[j]
                        else:
                            df.at[i, col] = None

            # Перезаписываем файл с изменениями для всех страниц
            df.to_csv(file_name, index=False, sep=';')
            st.success(f"Изменения сохранены для всех страниц в файл: {file_name}")
        except Exception as e:
            st.error(f"Ошибка при сохранении файла: {e}")

if __name__ == "__main__":
    file_name = "update_assortment.csv"  # Замените на имя вашего файла
    main(file_name, rows_per_page=10)
