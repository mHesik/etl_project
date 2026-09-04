# Импорты
import pandas as pd
import json
import sqlite3
import pathlib
import datetime
import logging
import requests

# настройка логирования
logs_folder = pathlib.Path('logs')
logs_folder.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=logs_folder / "etl.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

# функция дернуть с апи данные
def extract():
    logging.info("Началась загрузка данных")
    # константа ссылки

    limit = 30
    skip = 0

    all_products = []
    # обработка исключение try except
    try:
        while True:
            url = f'https://dummyjson.com/products?limit={limit}&skip={skip}'

            r = requests.get(url, timeout=5)

            logging.info(f"Статус ответа: {r.status_code}")

            r.raise_for_status()

            data = r.json()
            products = data["products"]

            logging.info(f"Получено строк от API: {len(r.json()["products"])}, skip={skip}")

            all_products.extend(products)

            skip += limit

            if skip >= data["total"]:
                break

            logging.info(
                f"Всего загружено товаров: {len(all_products)}"
            )

        return all_products
            
    except requests.exceptions.RequestException:
        logging.error("Произошла ошибка запроса")
        return None

def save_json(raw_data):
    if raw_data is not None:
        # получаем json
        # задаем переменную с путем к raw
        raw_folder = pathlib.Path("data/raw")
        # создаем папку, parents = создать все семейство папок, exist = если есть то не надо
        raw_folder.mkdir(parents=True, exist_ok=True)
        # указываем конретный путь иназвание файла
        file_path = raw_folder / 'products.json'

        # открыть файл(open()) для записи("w"-запись), после выполнения вложенного блока with закрывает файл
        with file_path.open("w", encoding="utf-8") as file:
            # json.dump(что_записываем, куда_записываем, настройки)
            # ensure_ascii=False — сохранять русские символы как обычный текст;
            # indent=2 — красиво форматировать JSON с отступами в 2 пробела.
            json.dump(raw_data, file, ensure_ascii=False, indent=2)
        logging.info("JSON успешно сохранен")
    else:
        logging.error("JSON не сохранён: данные отсутствуют")

# функция чтения сырого json
def read_json():
    # путь в котором лежит сырой json
    file_path = pathlib.Path('data/raw/products.json')

    try:
        file = file_path.read_text(encoding="utf-8")
        logging.info("JSON Файл найден")
        # функция with которая читает и загружаета данные из файла
        with file_path.open('r', encoding='utf-8') as file:
            raw_data = json.load(file)
    
        return raw_data
    
    except FileNotFoundError:
        logging.error("JSON Файл отсутствует!")
        return None

    except json.JSONDecodeError:
        logging.error("JSON Файл повреждён!")
        return None
    
def make_summary(df):
    summary = (
        df.groupby('категория')
            .agg(
                количество=("название", "count"),
                средняя_цена=("цена", "mean")
        )
    .reset_index()
    )
    # округлить среднюю цену до 2 символов после запятой
    summary["средняя_цена"] = summary["средняя_цена"].round(2)
    return summary



# функция сохранения обработанного Дата Фрейма в формат csv
def save_csv(df, filename):
    if df is not None:
        proc_folder = pathlib.Path("data/processed")
        proc_folder.mkdir(parents=True, exist_ok=True)
        name = filename + '.csv'
        file_path = proc_folder / name
        df.to_csv(file_path, index=False, encoding="utf-8-sig", sep=";")
        logging.info("CSV успешно сохранен")
    else:
        logging.error("Датафрейм пустой")

# Функция обработки данных
def transform(all_products):
    logging.info("Обработка данных началась")
    
    if all_products is None:
        return None

    # Нормализация Json
    df = pd.json_normalize(all_products)

    if df["id"].duplicated().any():
                logging.error("Обнаружены дубликаты id")
                return None

    #Проверка на обязательные поля
    required_columns = {"title", "category", "price"}

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        logging.error(f"Ошибка отсутствуют обязательные поля: {missing_columns}")
        return None
    else:
        logging.info("Все обязательные поля на месте")
        #Если ничего нет, то есть  Null ставим Не указан
        df["brand"] = df["brand"].fillna("Не указан")
    
    
        # Убрать не нужный столбец
        df = df.drop(columns=[
            'meta.qrCode',
            'reviews',
            'images',
            'thumbnail',
            'meta.barcode',
            'tags',
            'sku',
            'warrantyInformation',
            'shippingInformation',
            'returnPolicy',
            'dimensions.width',
            "dimensions.height",
            "dimensions.depth",
            'minimumOrderQuantity',
            "meta.createdAt",
            "meta.updatedAt"                   
        ])
    
        # Переименовать столбцы
        df = df.rename(columns={
            'title': 'название',
            'description': 'описание',
            'category': 'категория',
            'price': 'цена',
            'discountPercentage': 'процент_скидки',
            'rating': "рейтинг",
            "stock": "количество",
            "brand": "бренд",
            "weight": "вес",
            "availabilityStatus": "статус_остатка"
        })
    
        # указать типы данных явно
        df = df.astype({
            "id": "int64",
            "цена": "float64",
            "процент_скидки": "float64",
            "рейтинг": "float64",
            "количество": "int64",
            "вес": "int64",
            "название": "string",
            "описание": "string",
            "категория": "string",
            "бренд": "string",
            "статус_остатка": "string"
        })
    
        logging.info(f"Осталось строк после обработки {len(df)}")
        logging.info(f"\nТипы данных\n{df.dtypes}")
    
        # Преобразование данных в строки, если данные были списками или словарями
        # df = df.map(lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x)
        return df
    


# Функция заливки данных в SQL
def load(df):
    proc_folder = pathlib.Path("data/processed")
    proc_folder.mkdir(parents=True, exist_ok=True)
    file_path = proc_folder / 'my_db.db'

    # Подключение к бд, если нет то создание
    with sqlite3.connect(file_path) as conn:

        cursor = conn.cursor()
        rows = list(df.itertuples(index=False, name=None))
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products(
                id    INTEGER PRIMARY KEY,
                название             TEXT,
                описание             TEXT,
                категория            TEXT,
                цена                 REAL,
                процент_скидки       REAL,
                рейтинг              REAL,
                количество        INTEGER,
                бренд                TEXT,
                вес               INTEGER,
                статус_остатка       TEXT
            )
''')

        cursor.execute("DELETE FROM products")

        cursor.executemany("INSERT INTO products (id, название, описание, категория, цена, процент_скидки, рейтинг, количество, бренд, вес, статус_остатка) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           rows
                           )


        logging.info("Данные успешно сохранены в SQLite")


# Основная функция которая вызывает все остальное
def main():

    
    raw_data = extract()
    if raw_data is not None:
        save_json(raw_data)
        raw_data = read_json()
        

        if raw_data:
            # Вызывает функцию очистки данных
            df = transform(raw_data)
            summary = make_summary(df)
            # вызывает функцию заливки данных
            load(df)
            save_csv(df, "products_processed")
            save_csv(summary, "summary")
            return df
    else:
        logging.error("Json путсой")

   
# Умная штука __Name__ принимает скрытый параметр, программа запущена как модуль или самостоятельно
# Шляпа в зависимости от __name__ вызывает себя по разному
if __name__ == "__main__":
    df_ready = main()