import streamlit as st
import requests
from datetime import datetime, date
import os
from dotenv import load_dotenv


# Configuración de la página
st.set_page_config(
    page_title="Disponibilidad de dispositivos",
    page_icon="",
    layout="centered"
)

# Logo + título en la misma línea (alineados a la izquierda)
logo_col, title_col = st.columns([1, 9])

with logo_col:
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    st.image("img/icono.png", width=80)

with title_col:
    st.markdown("<h1 style='margin-top: 20px;'>Disponibilidad de dispositivos</h1>", unsafe_allow_html=True)

st.markdown("Consulta qué dispositivos están disponibles para alquilar en un rango de fechas")
st.markdown("---")

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de Notion
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_VERSION = "2022-06-28"
DEVICES_ID = "43e15b677c8c4bd599d7c602f281f1da"
LOCATIONS_ID = "28758a35e4118045abe6e37534c44974"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


def get_pages(database_id):
    """Obtiene todas las páginas de una base de datos de Notion"""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {"page_size": 100}
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    
    return data.get("results", [])


def extract_device_data(page):
    """Extrae los campos específicos de cada dispositivo"""
    props = page["properties"]
    device_data = {}
    
    # Extraer ID de la página
    device_data["id"] = page["id"]
    
    # Extraer Name
    try:
        if props.get("Name") and props["Name"]["title"]:
            device_data["Name"] = props["Name"]["title"][0]["text"]["content"]
        else:
            device_data["Name"] = "Sin nombre"
    except:
        device_data["Name"] = "Sin nombre"
    
    # ========================================
    # 🔹 CORREGIDO: Extraer Tags (campo SELECT, no multi_select)
    # ========================================
    # Tags es un campo "select" que contiene UN SOLO VALOR
    # Ejemplo: "Ultra" o "Neo 4"
    try:
        if props.get("Tags") and props["Tags"]["select"]:
            # Extraemos el nombre del tag seleccionado
            device_data["Tags"] = props["Tags"]["select"]["name"]
        else:
            device_data["Tags"] = "Sin tag"
    except:
        device_data["Tags"] = "Sin tag"
    # ========================================
    
    # Extraer Locations_demo
    try:
        if props.get("Location") and props["Location"]["relation"]:
            location_ids = [rel["id"] for rel in props["Location"]["relation"]]
            device_data["Locations_demo_count"] = len(location_ids)
        else:
            device_data["Locations_demo_count"] = 0
    except:
        device_data["Locations_demo_count"] = 0
    
    # Extraer Start Date
    try:
        if props.get("Start Date") and props["Start Date"]["rollup"]:
            rollup = props["Start Date"]["rollup"]
            if rollup["type"] == "date" and rollup.get("date"):
                device_data["Start Date"] = rollup["date"]["start"]
            elif rollup["type"] == "array" and rollup["array"]:
                first_item = rollup["array"][0]
                if first_item["type"] == "date" and first_item.get("date"):
                    device_data["Start Date"] = first_item["date"]["start"]
                else:
                    device_data["Start Date"] = None
            else:
                device_data["Start Date"] = None
        else:
            device_data["Start Date"] = None
    except:
        device_data["Start Date"] = None
    
    # Extraer End Date
    try:
        if props.get("End Date") and props["End Date"]["rollup"]:
            rollup = props["End Date"]["rollup"]
            if rollup["type"] == "date" and rollup.get("date"):
                device_data["End Date"] = rollup["date"]["start"]
            elif rollup["type"] == "array" and rollup["array"]:
                first_item = rollup["array"][0]
                if first_item["type"] == "date" and first_item.get("date"):
                    device_data["End Date"] = first_item["date"]["start"]
                else:
                    device_data["End Date"] = None
            else:
                device_data["End Date"] = None
        else:
            device_data["End Date"] = None
    except:
        device_data["End Date"] = None
    
    return device_data


def check_availability(device, start_date, end_date):
    """Verifica si un dispositivo está disponible en el rango de fechas"""
    
    # Sin ubicación = disponible
    if device["Locations_demo_count"] == 0:
        return True
    
    # Tiene ubicación, verificar fechas
    device_start = device["Start Date"]
    device_end = device["End Date"]
    
    # Con ubicación pero sin fechas = ocupado indefinidamente
    if device_start is None and device_end is None:
        return False
    
    # Convertir strings a objetos date
    try:
        if device_start:
            device_start_date = datetime.fromisoformat(device_start).date()
        else:
            device_start_date = None
            
        if device_end:
            device_end_date = datetime.fromisoformat(device_end).date()
        else:
            device_end_date = None
    except:
        return False
    
    # Verificar solapamiento
    if device_start_date and device_end_date:
        if (start_date <= device_end_date and end_date >= device_start_date):
            return False
        else:
            return True
    
    elif device_start_date and not device_end_date:
        if end_date >= device_start_date:
            return False
        else:
            return True
    
    elif device_end_date and not device_start_date:
        if start_date <= device_end_date:
            return False
        else:
            return True
    
    return True


def get_in_house_locations():
    """Obtiene locations de tipo In House con contador de devices desde campo Units"""
    url = f"https://api.notion.com/v1/databases/{LOCATIONS_ID}/query"
    
    payload = {
        "filter": {
            "property": "Type",
            "select": {
                "equals": "In House"
            }
        },
        "page_size": 100
    }
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    
    locations = []
    for page in data.get("results", []):
        props = page["properties"]
        
        # Extraer Name
        try:
            if props.get("Name") and props["Name"]["title"]:
                name = props["Name"]["title"][0]["text"]["content"]
            else:
                name = "Sin nombre"
        except:
            name = "Sin nombre"
        
        # Extraer Units como device_count
        try:
            if props.get("Units") and props["Units"]["number"] is not None:
                device_count = props["Units"]["number"]
            else:
                device_count = 0
        except:
            device_count = 0
        
        locations.append({
            "id": page["id"],
            "name": name,
            "device_count": device_count
        })
    
    return locations


def create_in_house_location(name, start_date):
    """Crea una nueva location In House en Notion"""
    url = "https://api.notion.com/v1/pages"
    
    payload = {
        "parent": {"database_id": LOCATIONS_ID},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": name
                        }
                    }
                ]
            },
            "Type": {
                "select": {
                    "name": "In House"
                }
            },
            "Start Date": {
                "date": {
                    "start": start_date.isoformat()
                }
            }
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        st.success(f"✅ Ubicación '{name}' creada correctamente")
        return data["id"]
    else:
        st.error(f"❌ Error al crear ubicación: {response.text}")
        return None


def assign_devices_client(device_names, client_name, start_date, end_date, available_devices):
    """Asigna dispositivos a un cliente (crea nueva location Client)"""
    
    if not client_name or client_name.strip() == "":
        st.error("⚠️ El nombre del destino no puede estar vacío")
        return False
    
    # 1. Crear la location Client
    url_location = "https://api.notion.com/v1/pages"
    
    payload_location = {
        "parent": {"database_id": LOCATIONS_ID},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": client_name
                        }
                    }
                ]
            },
            "Type": {
                "select": {
                    "name": "Client"
                }
            },
            "Start Date": {
                "date": {
                    "start": start_date.isoformat()
                }
            },
            "End Date": {
                "date": {
                    "start": end_date.isoformat()
                }
            }
        }
    }
    
    with st.spinner(f"Creando destino '{client_name}'..."):
        response_location = requests.post(url_location, json=payload_location, headers=headers)
    
    if response_location.status_code != 200:
        st.error(f"❌ Error al crear el destino: {response_location.text}")
        return False
    
    location_data = response_location.json()
    location_id = location_data["id"]
    
    st.success(f"✅ Destino '{client_name}' creado")
    
    # 2. Asignar cada dispositivo a esta location
    success_count = 0
    url_patch = "https://api.notion.com/v1/pages/"
    
    progress_bar = st.progress(0)
    total = len(device_names)
    
    for idx, device_name in enumerate(device_names):
        # Buscar el device_id en available_devices
        device_id = None
        for device in available_devices:
            if device["Name"] == device_name:
                device_id = device["id"]
                break
        
        if not device_id:
            st.warning(f"⚠️ No se encontró el ID para '{device_name}'")
            continue
        
        payload_device = {
            "properties": {
                "Location": {   # Cambiado de 📍 Locations_demo
                    "relation": [
                        {"id": location_id}
                    ]
                }
            }
        }
                
        response_device = requests.patch(f"{url_patch}{device_id}", json=payload_device, headers=headers)
        
        if response_device.status_code == 200:
            success_count += 1
        else:
            st.warning(f"⚠️ Error al asignar '{device_name}': {response_device.text}")
        
        progress_bar.progress((idx + 1) / total)
    
    progress_bar.empty()
    
    if success_count == len(device_names):
        st.success(f"🎉 ¡Perfecto! {success_count} dispositivos asignados a '{client_name}'")
        return True
    elif success_count > 0:
        st.warning(f"⚠️ Se asignaron {success_count} de {len(device_names)} dispositivos")
        return True
    else:
        st.error("❌ No se pudo asignar ningún dispositivo")
        return False


def assign_devices_in_house(device_names, location_id, location_name, start_date, available_devices):
    """Asigna dispositivos a una ubicación In House existente"""
    
    success_count = 0
    url_patch = "https://api.notion.com/v1/pages/"
    
    progress_bar = st.progress(0)
    total = len(device_names)
    
    for idx, device_name in enumerate(device_names):
        # Buscar el device_id en available_devices
        device_id = None
        for device in available_devices:
            if device["Name"] == device_name:
                device_id = device["id"]
                break
        
        if not device_id:
            st.warning(f"⚠️ No se encontró el ID para '{device_name}'")
            continue
        
        payload_device = {
            "properties": {
                "Location": {   # Cambiado de 📍 Locations_demo
                    "relation": [
                        {"id": location_id}
                    ]
                }
            }
        }
        
        response_device = requests.patch(f"{url_patch}{device_id}", json=payload_device, headers=headers)
        
        if response_device.status_code == 200:
            success_count += 1
        else:
            st.warning(f"⚠️ Error al asignar '{device_name}': {response_device.text}")
        
        progress_bar.progress((idx + 1) / total)
    
    progress_bar.empty()
    
    if success_count == len(device_names):
        st.success(f"🎉 ¡Perfecto! {success_count} dispositivos asignados a '{location_name}'")
        return True
    elif success_count > 0:
        st.warning(f"⚠️ Se asignaron {success_count} de {len(device_names)} dispositivos")
        return True
    else:
        st.error("❌ No se pudo asignar ningún dispositivo")
        return False


# Inicializar estado de sesión
if 'selected_devices' not in st.session_state:
    st.session_state.selected_devices = []

if 'search_completed' not in st.session_state:
    st.session_state.search_completed = False

if 'available_devices' not in st.session_state:
    st.session_state.available_devices = []

if 'query_start_date' not in st.session_state:
    st.session_state.query_start_date = date.today()

if 'query_end_date' not in st.session_state:
    st.session_state.query_end_date = date.today()


# Interfaz de fechas
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input(
        "Fecha de inicio",
        value=date.today(),
        format="DD/MM/YYYY"
    )

with col2:
    end_date = st.date_input(
        "Fecha de fin",
        value=date.today(),
        format="DD/MM/YYYY"
    )

# Validación de fechas
if start_date > end_date:
    st.error("⚠️ La fecha de inicio no puede ser posterior a la fecha de fin")
    st.stop()

# Botón de búsqueda
if st.button("🔍 Consultar Disponibilidad", type="primary", use_container_width=True):
    with st.spinner("Consultando dispositivos..."):
        # Obtener todos los devices
        pages = get_pages(DEVICES_ID)
        all_devices = [extract_device_data(page) for page in pages]
        
        # Filtrar disponibles
        available_devices = [
            device for device in all_devices 
            if check_availability(device, start_date, end_date)
        ]
        
        # Guardar en session_state
        st.session_state.available_devices = available_devices
        st.session_state.query_start_date = start_date
        st.session_state.query_end_date = end_date
        st.session_state.search_completed = True
        st.session_state.selected_devices = []

# Mostrar resultados si la búsqueda se completó
if st.session_state.search_completed:
    available_devices = st.session_state.available_devices
    
    if available_devices:
        st.success(f"✅ Hay {len(available_devices)} dispositivos disponibles")
        
        # ========================================
        # 🔹 CORREGIDO: Obtener tags únicos (select, no multi_select)
        # ========================================
        # Como Tags es un campo "select" con un solo valor por dispositivo,
        # simplemente recopilamos todos los valores únicos
        
        unique_tags = set()  # Set para evitar duplicados
        for device in available_devices:
            # Cada dispositivo tiene un solo tag (string)
            if device["Tags"] and device["Tags"] != "Sin tag":
                unique_tags.add(device["Tags"])
        
        # Convertir a lista ordenada
        unique_tags = sorted(unique_tags)
        
        # Añadir "Todos" como primera opción
        filter_options = ["Todos"] + unique_tags
        # ========================================
        
        # ========================================
        # 🔹 Selector de filtro por Tag
        # ========================================
        st.markdown("---")
        selected_tag = st.selectbox(
            "🔍 Filtrar por etiqueta",
            options=filter_options,
            index=0  # "Todos" seleccionado por defecto
        )
        # ========================================
        
        # ========================================
        # 🔹 CORREGIDO: Aplicar filtro (comparación directa)
        # ========================================
        # Ahora comparamos directamente el string del tag
        if selected_tag == "Todos":
            filtered_devices = available_devices
        else:
            # Filtramos: un dispositivo se incluye si su tag coincide exactamente
            filtered_devices = [d for d in available_devices if d["Tags"] == selected_tag]
        # ========================================
        
        # Mostrar contador de dispositivos filtrados
        if selected_tag != "Todos":
            st.info(f"📊 Mostrando {len(filtered_devices)} dispositivos con etiqueta '{selected_tag}'")
        
        # Ordenar alfabéticamente los dispositivos filtrados
        available_devices_sorted = sorted(filtered_devices, key=lambda d: d["Name"])
        
        # Selector de dispositivos con checkboxes
        st.markdown("---")
        st.subheader("Selecciona los dispositivos que quieres asignar")
        
        # Mostrar los dispositivos ordenados y filtrados
        for device in available_devices_sorted:
            device_name = device["Name"]
            
            # Columnas para checkbox y cajetín
            inner_col1, inner_col2 = st.columns([0.5, 9.5])
            
            with inner_col1:
                # Checkbox
                checkbox_value = st.checkbox(
                    "",
                    value=device_name in st.session_state.selected_devices,
                    key=f"check_{device_name}",
                    label_visibility="collapsed"
                )
                
                # Actualizar lista de seleccionados
                if checkbox_value and device_name not in st.session_state.selected_devices:
                    st.session_state.selected_devices.append(device_name)
                elif not checkbox_value and device_name in st.session_state.selected_devices:
                    st.session_state.selected_devices.remove(device_name)
            
            with inner_col2:
                # Solo mostrar el nombre (sin tags)
                st.markdown(
                    f"""
                    <div style='padding: 8px 12px; 
                                background-color: {"#B3E5E6" if checkbox_value else "#e0e0e0"}; 
                                border-radius: 6px; 
                                margin-top: -8px;
                                border-left: 4px solid {"#00859B" if checkbox_value else "#9e9e9e"};'>
                        <p style='margin: 0; font-size: 16px; font-weight: 500; color: #333;'>
                            {device_name}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            # Espacio entre dispositivos
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        # Mostrar formulario de asignación si hay dispositivos seleccionados
        if st.session_state.selected_devices:
            st.markdown("---")
            st.subheader(f"🎯 Asignar ubicación ({len(st.session_state.selected_devices)} dispositivos)")
            
            # Selector de tipo de ubicación - DESPLEGABLE
            location_type = st.selectbox(
                "Tipo de Ubicación",
                ["Client", "In House"],
                index=0  # Client por defecto
            )
            
        
            
            # Información de dispositivos seleccionados
            selected_list = ", ".join(st.session_state.selected_devices)
            st.info(f"**Seleccionados:** {selected_list}")
            
            # Mostrar fechas según el tipo
            if location_type == "Client":
                query_start = st.session_state.query_start_date
                query_end = st.session_state.query_end_date
                st.info(f"📅 **Fechas:** {query_start.strftime('%d/%m/%Y')} - {query_end.strftime('%d/%m/%Y')}")
            else:  # In House
                today = date.today()
                st.info(f"📅 **Fecha de inicio:** {today.strftime('%d/%m/%Y')}")
            
            st.markdown("---")
            
            # Formulario según el tipo
            if location_type == "Client":
                # FORMULARIO CLIENT
                st.write("**📋 Nuevo Destino Cliente**")
                
                client_name = st.text_input(
                    "Nombre del Destino",
                    placeholder="Ej: Destino Barcelona 2025",
                    key="client_name_input"
                )
                
                if st.button("Asignar", type="primary", use_container_width=True):
                    query_start = st.session_state.query_start_date
                    query_end = st.session_state.query_end_date
                    
                    # Usamos available_devices original (lista completa)
                    success = assign_devices_client(
                        st.session_state.selected_devices,
                        client_name,
                        query_start,
                        query_end,
                        st.session_state.available_devices
                    )
                    
                    if success:
                        st.session_state.selected_devices = []
                        st.session_state.search_completed = False
                        st.session_state.available_devices = []
                        st.rerun()
            
            else:
                # FORMULARIO IN HOUSE
                st.write("**🏠 Asignar a In House**")
                
                # Obtener locations In House
                with st.spinner("Cargando ubicaciones In House..."):
                    in_house_locations = get_in_house_locations()
                
                if not in_house_locations:
                    st.warning("⚠️ No hay ubicaciones In House disponibles")
                    st.info("💡 Crea una nueva ubicación In House")
                    
                    # Formulario para crear nueva
                    new_in_house_name = st.text_input(
                        "Nombre de la ubicación",
                        placeholder="Ej: Casa Juan",
                        key="new_in_house_name"
                    )
                    
                    if st.button("Crear y Asignar", type="primary", use_container_width=True):
                        if not new_in_house_name or new_in_house_name.strip() == "":
                            st.error("⚠️ El nombre no puede estar vacío")
                        else:
                            today = date.today()
                            with st.spinner("Creando ubicación..."):
                                location_id = create_in_house_location(new_in_house_name, today)
                            
                            if location_id:
                                success = assign_devices_in_house(
                                    st.session_state.selected_devices,
                                    location_id,
                                    new_in_house_name,
                                    today,
                                    st.session_state.available_devices
                                )
                                
                                if success:
                                    st.session_state.selected_devices = []
                                    st.session_state.search_completed = False
                                    st.session_state.available_devices = []
                                    st.rerun()
                
                else:
                    # Mostrar dropdown con locations existentes
                    location_options = {
                        f"📍 {loc['name']} ({loc['device_count']} devices)": loc['id'] 
                        for loc in in_house_locations
                    }
                    
                    selected_location_display = st.selectbox(
                        "Seleccionar ubicación existente",
                        options=list(location_options.keys())
                    )
                    
                    selected_location_id = location_options[selected_location_display]
                    selected_location_name = selected_location_display.split(" (")[0].replace("📍 ", "")
                    
                    # Opción para crear nueva
                    with st.expander("➕ O crear nueva ubicación In House"):
                        new_in_house_name = st.text_input(
                            "Nombre de la ubicación",
                            placeholder="Ej: Casa María",
                            key="new_in_house_name_alt"
                        )
                        
                        if st.button("Crear y Asignar Nueva", type="secondary", use_container_width=True):
                            if not new_in_house_name or new_in_house_name.strip() == "":
                                st.error("⚠️ El nombre no puede estar vacío")
                            else:
                                today = date.today()
                                with st.spinner("Creando ubicación..."):
                                    location_id = create_in_house_location(new_in_house_name, today)
                                
                                if location_id:
                                    success = assign_devices_in_house(
                                        st.session_state.selected_devices,
                                        location_id,
                                        new_in_house_name,
                                        today,
                                        st.session_state.available_devices
                                    )
                                    
                                    if success:
                                        st.session_state.selected_devices = []
                                        st.session_state.search_completed = False
                                        st.session_state.available_devices = []
                                        st.rerun()
                    
                    # Botón principal para asignar a existente
                    if st.button("Asignar", type="primary", use_container_width=True):
                        today = date.today()
                        success = assign_devices_in_house(
                            st.session_state.selected_devices,
                            selected_location_id,
                            selected_location_name,
                            today,
                            st.session_state.available_devices
                        )
                        
                        if success:
                            st.session_state.selected_devices = []
                            st.session_state.search_completed = False
                            st.session_state.available_devices = []
                            st.rerun()
    
    else:
        st.warning("⚠️ No hay dispositivos disponibles en estas fechas")

else:
    st.info("👆 Selecciona las fechas y haz clic en 'Consultar Disponibilidad'")