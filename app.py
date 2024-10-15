import streamlit as st
import pandas as pd
import math
from PIL import Image
import requests
from io import BytesIO

# Функция для загрузки изображения с URL
def load_image_from_url(url, idx):
    # Проверяем, было ли уже загружено изображение для данного URL
    if f'image_{idx}' not in st.session_state:
        try:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            img.load()  # Загружаем изображение для дальнейшего использования
            # Сохраняем изображение и его размер в сессию
            st.session_state[f'image_{idx}'] = (img, response.headers.get('Content-Length', None))
        except Exception:
            st.session_state[f'image_{idx}'] = (None, None)
    return st.session_state[f'image_{idx}']  # Возвращаем кэшированное изображение

# Функция для отображения данных постранично и изменения порядка изображений
def display_data(df, image_columns, start, end):
    for i in range(start, end):
        row = df.iloc[i]

        # Проверяем, существует ли столбец 'Код артикула' и выводим его значение
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

        # Отображаем изображения, только если есть хотя бы одно изображение
        if images:
            # Создаем скроллбар для изображений
            scroll_container = st.container()
            with scroll_container:
                cols = st.columns(min(10, len(images)))
                for idx, img_idx in enumerate(st.session_state[f'order_{i}']):
                    with cols[idx % 10]:
                        img_url = images[img_idx]
                        unique_key = f'{i}_{img_idx}_{idx}'
                        img, img_size = load_image_from_url(img_url, unique_key)
                        if img:
                            st.image(img, width=100)
                            img_width, img_height = img.size
                            formatted_size = f"{img_width}x{img_height}"
                            formatted_weight = f"{int(img_size)/1024:.2f} KB" if img_size else "Размер неизвестен"
                            # st.caption(f"Размер: {formatted_size}")
                            # st.caption(f"Вес: {formatted_weight}")
                        else:
                            # Показать "bad link", если изображение не удалось загрузить
                            st.markdown(f"""
                                <div style='width:100px;height:100px;background-color:grey;display:flex;align-items:center;justify-content:center;color:white;flex-direction:column;'>
                                    <span>bad link</span>
                                    <a href='{img_url}' target='_blank' style='color:white; text-decoration:none;'>🔗</a>
                                </div>
                            """, unsafe_allow_html=True)

                        # Контейнер для кнопок перемещения
                        with st.container():
                            # Кнопка для удаления изображения
                            if st.button(f'❌', key=f'delete_{unique_key}'):
                                st.session_state[f'order_{i}'].remove(img_idx)
                                df.at[i, image_columns[img_idx]] = None

                            # Кнопка для перемещения изображения в начало списка (если это не первое изображение)
                            if idx > 0:
                                if st.button(f'⬅️', key=f'to_start_{unique_key}'):
                                    st.session_state[f'order_{i}'].insert(0, st.session_state[f'order_{i}'].pop(idx))

                            # Кнопка для перемещения изображения в конец списка (если это не последнее изображение)
                            if idx < len(st.session_state[f'order_{i}']) - 1:
                                if st.button(f'➡️', key=f'to_end_{unique_key}'):
                                    st.session_state[f'order_{i}'].append(st.session_state[f'order_{i}'].pop(idx))

                # Обновляем порядок изображений в DataFrame сразу после изменения
                reordered_images = [df.loc[i, image_columns[j]] for j in st.session_state[f'order_{i}']]
                for j, col in enumerate(image_columns):
                    if j < len(reordered_images):
                        df.at[i, col] = reordered_images[j]
                    else:
                        df.at[i, col] = None

        st.write("---")


# Основная функция
def main(rows_per_page=10):
    st.title("Редактирование данных CSV")

    # Загрузка CSV файла
    uploaded_file = st.file_uploader("Загрузите CSV файл", type=["csv"])

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=';', dtype=str)
        except Exception as e:
            st.error(f"Ошибка загрузки файла: {e}")
            return

        # Проверяем, какие столбцы есть в DataFrame
        st.write("Доступные столбцы в файле:")
        st.write(df.columns.tolist())

        # Определяем столбцы с изображениями
        image_columns = [col for col in df.columns if col.startswith('Изображения товаров')]

        # Постраничный вывод
        total_rows = df.shape[0]
        total_pages = math.ceil(total_rows / rows_per_page)

        if 'orders' not in st.session_state:
            st.session_state.orders = {}
            for i in range(total_rows):
                row_images = [df.loc[i, col] for col in image_columns if pd.notna(df.loc[i, col])]
                st.session_state.orders[i] = list(range(len(row_images)))
        # Инициализируем страницу
        if 'page' not in st.session_state:
            st.session_state.page = 1

        # Слайдер для выбора страницы
        if total_pages > 1:
            st.session_state.page = st.slider("Выберите страницу", min_value=1, max_value=total_pages, value=st.session_state.page)
        else:
            st.session_state.page = 1

        # Ввод номера страницы
        st.session_state.page = st.number_input("Введите номер страницы", min_value=1, max_value=total_pages, value=st.session_state.page)

        # Вычисляем строки для отображения
        start_row = (st.session_state.page - 1) * rows_per_page
        end_row = min(start_row + rows_per_page, total_rows)

        # Отображаем данные
        display_data(df, image_columns, start_row, end_row)

        # Кнопка для сохранения изменений внизу страницы
        # Кнопка для сохранения изменений внизу страницы
        if st.button("Сохранить изменения в CSV"):
            # Применяем изменения для всех строк, а не только для текущей страницы
            for i in range(total_rows):
                if f'order_{i}' in st.session_state:
                    order = st.session_state[f'order_{i}']
                    reordered_images = [df.loc[i, image_columns[j]] for j in order]

                    # Обновляем столбцы с изображениями
                    for j, col in enumerate(image_columns):
                        if j < len(reordered_images):
                            df.at[i, col] = reordered_images[j]
                        else:
                            df.at[i, col] = None

            # Создание CSV для скачивания
            csv = df.to_csv(index=False, sep=';').encode('utf-8')

            st.download_button(
                label="Скачать обновлённый CSV",
                data=csv,
                file_name='update_assortment.csv',
                mime='text/csv',
            )


if __name__ == "__main__":
    main(rows_per_page=10)
