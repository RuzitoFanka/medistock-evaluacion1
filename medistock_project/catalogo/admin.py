from django.contrib import admin
from django.db import models
from django import forms
from .models import Producto, Bodega, BodegaStock

# =========================================================================
# CONFIGURACIÓN AVANZADA PANEL DE ADMINISTRACIÓN - MEDISTOCK
# =========================================================================

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # 🛡️ Sobreescribe el cuadro de texto visual en el navegador.
    # Fuerza a que el mínimo permitido sea 0, impidiendo bajar a negativos con las flechas.
    formfield_overrides = {
        models.DecimalField: {
            'widget': forms.NumberInput(attrs={
                'min': '0', 
                'step': '1',
                'style': 'width: 150px;'
            })
        },
    }
    
    # Columnas visibles en el listado del administrador
    list_display = ('codigo_producto', 'nombre', 'precio_unitario', 'stock_minimo')
    search_fields = ('codigo_producto', 'nombre')

    # 🚫 INTERCEPCIÓN DE LOGS: Desactiva por completo el historial de auditoría
    # Esto evita que los productos aparezcan como "fantasmas" en la barra lateral gris
    def log_addition(self, request, object, message):
        """ Desactiva el log cuando creas un producto """
        pass

    def log_change(self, request, object, message):
        """ Desactiva el log cuando editas un producto """
        pass

    def log_deletion(self, request, object, object_repr):
        """ Desactiva el log cuando eliminas un producto """
        pass


# 🏢 Registro del resto de tus modelos para la gestión de inventarios y sucursales
@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')


@admin.register(BodegaStock)
class BodegaStockAdmin(admin.ModelAdmin):
    list_display = ('producto', 'bodega', 'stock')
    list_filter = ('bodega',)