from django.contrib import admin
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
# Agregamos 'login_view' a tus importaciones existentes
from catalogo.views import (
    ConsultaStockAPIView, ProcesarPagoAPIView, GenerarTrackingAPIView, 
    vista_tienda, procesar_compra_view, resumen_orden_view, login_view
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 🔐 Nueva ruta asignada para el módulo de login
    path('login/', login_view, name='login'),
    
    # Rutas del portal web que ya tenías
    path('', vista_tienda, name='pantalla-tienda'),
    path('procesar-compra/', procesar_compra_view, name='procesar_compra'),
    path('resumen-orden/', resumen_orden_view, name='resumen_orden'),
    
    # Endpoints de la API REST que ya tenías
    path('api/v1/auth/', obtain_auth_token, name='api-token'),
    path('api/v1/productos/<str:codigo_producto>/', ConsultaStockAPIView.as_view(), name='consulta-stock'),
    path('api/v1/pagos/procesar/', ProcesarPagoAPIView.as_view(), name='procesar-pago'),
    path('api/v1/logistica/tracking/', GenerarTrackingAPIView.as_view(), name='generar-tracking'),
]