import re
import json
import os
from urllib.parse import urljoin
import requests
from playwright.sync_api import sync_playwright, Playwright
from logger import setup_logger


HOME_PAGE_URL = "https://www.baldor.com"
CATALOG_URL = "https://www.baldor.com/catalog/#category=69" # URL for where the scraping starts 

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/pdf,image/*",
}

logger = setup_logger('baldor')

def save_product_data(**kwargs):
    try:
        product_id = kwargs["product_id"]
        manual_url = kwargs.get("manual_url")
        image_url = kwargs.get("image_url")
        description = kwargs.get("description", "")
        hp = kwargs.get("hp", "")
        voltage = kwargs.get("voltage", "")
        rpm = kwargs.get("rpm", "")
        frame = kwargs.get("frame", "")
        parts_info = kwargs.get('parts_info', [])

        base_path = f"output/assets/{product_id}"
        os.makedirs(base_path, exist_ok=True)

        manual_path = f'{base_path}/manual.pdf' if manual_url else None
        image_path = f'{base_path}/img.png' if image_url else None

        if manual_url:
            download_file(manual_url, manual_path)
        if image_url:
            download_file(image_url, image_path)

        product_data = {
            "product_id": product_id,
            "name": "", # Not found in the products page
            "description": description,
            "specs": {
                "hp": hp,
                "voltage": voltage,
                "rpm": rpm,
                "frame": frame
            },
            "bom": parts_info,
            "assets": {
                "manual": manual_path if manual_url else None,
                "cad": None,
                "image": image_path if image_url else None
            }
        }

        json_path = f"output/{product_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(product_data, f, indent=2)
        logger.info(f"Saved JSON: {json_path}")
    except Exception as e:
        logger.error(f"Failed to save product data: {e}")

def download_file(url: str, output_path: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
        logger.info(f"Downloaded file from {url}")
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")

def get_all_products_available(page) -> tuple[str]:
    try:
        products_element = page.locator('div.overview').all()
        partial_urls = [el.locator('h3 a').get_attribute('href') for el in products_element]
        products_url = [urljoin(HOME_PAGE_URL, u) for u in partial_urls if u]
        return products_url, ""
    except Exception as e:
        logger.error(f"Failed to get all products: {e}")
        return [], ""

def start_page(p: Playwright):
    try:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        return page
    except Exception as e:
        logger.error(f"Failed to start page: {e}")
        raise

def get_product_id(page):
    try:
        return page.locator('.page-title h1').inner_text()
    except Exception as e:
        logger.error(f"Failed to get product ID: {e}")
        raise

def get_product_description(page):
    try:
        return page.locator('.product-description').inner_text()
    except Exception as e:
        logger.error(f"Failed to get product description: {e}")
        raise

def get_product_frame_number(page):
    try:
        element_path = 'xpath=(//span[contains(., "Frame")]//following-sibling::span)[1]'
        return page.locator(element_path).inner_text()
    except Exception as e:
        logger.error(f"Failed to get product frame number: {e}")
        raise

def get_product_rpm(page):
    element_path = 'xpath=(//span[.="Speed"]//following-sibling::span)[1]'
    try:
        web_element = page.locator(element_path)
        rpm_txt = web_element.inner_text().split('rpm')[0].strip()
        return rpm_txt
    except Exception as e:
        logger.error(f"Failed to get RPM: {e}")
        raise

def get_product_voltage(page):
    element_path = 'xpath=(//span[contains(., "Voltage")]//following-sibling::span)[1]'
    try:
        voltage_raw = page.locator(element_path).inner_text()
        voltage = '/'.join([v.split('V')[0].strip() for v in voltage_raw.split('\n') if 'V' in v])
        return voltage
    except Exception as e:
        logger.error(f"Failed to get voltage: {e}")
        raise

def get_product_hp(page):
    element_path = 'xpath=//span[contains(., "Output")]//following-sibling::span'
    try:
        hp_raw = page.locator(element_path).inner_text()
        hp = int(float(hp_raw.split('@')[0].split('HP')[0].strip()))
        return hp
    except Exception as e:
        logger.error(f"Failed to get HP: {e}")
        raise

def get_product_manual(page):
    try:
        return urljoin(HOME_PAGE_URL, page.locator('#infoPacket').get_attribute('href'))
    except Exception as e:
        logger.error(f"Failed to get manual URL: {e}")
        raise

def get_product_image(page):
    try:
        return urljoin(HOME_PAGE_URL, page.locator('.product-image').get_attribute('src'))
    except Exception as e:
        logger.error(f"Failed to get image URL: {e}")
        raise

def get_parts_info(page, product_url) -> list[dict]:
    elements_path = '.tab-content .pane.active .data-table tbody tr'
    try:
        page.goto(urljoin(product_url, '#tab="parts"'))
        rows_table_info = page.locator(elements_path).all()
        logger.debug(f'{len(rows_table_info)} many rows found in parts table:')
        list_dict_info = []

        for row in rows_table_info:
            try:
                part_number = row.first.locator('td:nth-child(1)').text_content().strip()
                description = row.first.locator('td:nth-child(2)').text_content().strip()
                quantity_raw = row.first.locator('td:nth-child(3)').text_content().strip()
                quantity = int(float(re.sub(r'[^\d.]', '', quantity_raw)))
                logger.info(
                    f'Part Number: {part_number} | Description: {description} | Quantity: {quantity}')
                list_dict_info.append({
                    'part_number': part_number,
                    'description': description,
                    'quantity': quantity
                })
            except Exception as e:
                logger.warning(f"Erro ao processar linha: {e}")
                continue
        return list_dict_info
    except Exception as e:
        logger.error(f"Failed to get parts info: {e}")
        return []

def main():
    with sync_playwright() as p:
        page = start_page(p)
        page.goto(CATALOG_URL)
        page.wait_for_selector('div.overview')
        products_url, _ = get_all_products_available(page)
        for product_url in products_url[:10]:
            try:
                page.goto(product_url)
                logger.info(f"Scraping product: {product_url}")
                page.wait_for_load_state("networkidle")
                product_id = get_product_id(page)
                logger.info(f"Product ID: {product_id}")
                description = get_product_description(page)
                frame = get_product_frame_number(page)
                rpm = get_product_rpm(page)
                voltage = get_product_voltage(page)
                hp = get_product_hp(page)
                manual_url = get_product_manual(page)
                image_url = get_product_image(page)
                parts_info = get_parts_info(page, product_url)

                save_product_data(
                    product_id=product_id,
                    description=description,
                    hp=hp,
                    voltage=voltage,
                    rpm=rpm,
                    frame=frame,
                    manual_url=manual_url,
                    image_url=image_url,
                    parts_info=parts_info
                )
            except Exception as e:
                logger.error(f"Error extracting product from {product_url}: {e}")
                continue

if __name__ == "__main__":
    main()
