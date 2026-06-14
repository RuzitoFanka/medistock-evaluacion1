from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from catalogo import views as catalogo_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 🛒 Páginas Web del Portal (Conectadas a tus funciones reales del views.py)
    path('', catalogo_views.vista_tienda, name='pantalla-tienda'),  
    
    # 📉 NUEVA RUTA INTEGRADA: Para recibir el carrito y descontar el stock en cascada (Global + Bodegas)
    path('tienda/procesar-pedido/', catalogo_views.procesar_pedido, name='procesar_pedido'),
    
    path('resumen-orden/', catalogo_views.resumen_orden_view, name='resumen_orden'),
    path('procesar-compra/', catalogo_views.procesar_compra_view, name='procesar_compra'),
    path('login/', catalogo_views.login_view, name='login'),
    
    # 🌐 Endpoints de la API REST (Llamando correctamente a tus clases de Rest Framework)
    path('api/v1/productos/<str:codigo_producto>/', catalogo_views.ConsultaStockAPIView.as_view(), name='consulta-stock'),
    path('api/v1/pagos/procesar/', catalogo_views.ProcesarPagoAPIView.as_view(), name='procesar-pago'),
    path('api/v1/logistica/tracking/', catalogo_views.GenerarTrackingAPIView.as_view(), name='generar-tracking'),
]

# 🔌 INYECTOR DE ARCHIVOS ESTÁTICOS (Fuerza la carga del style.css en modo DEBUG)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)