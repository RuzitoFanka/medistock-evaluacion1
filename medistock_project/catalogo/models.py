from django.db import models
from django.core.validators import MinValueValidator  # 🛡️ Protección contra valores negativos
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from django.contrib.admin.models import LogEntry

# =========================================================================
# MODELOS DE BASE DE DATOS (MEDISTOCK)
# =========================================================================

class Bodega(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    codigo_producto = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    
    # 🛡️ Campo protegido contra valores negativos usando MinValueValidator(0)
    precio_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # 🌟 Campo para las alertas de reabastecimiento
    stock_minimo = models.PositiveIntegerField(default=100)
    
    # 📊 CAMPO FÍSICO INTEGRADO: Guarda la sumatoria real sincronizada por señales
    stock_total = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.codigo_producto} - {self.nombre}"

    @property
    def requiere_reabastecimiento(self):
        # Si el stock total es menor o igual al mínimo, se gatilla la alerta
        return self.stock_total <= self.stock_minimo


class BodegaStock(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='existencias')
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'bodega')


# =========================================================================
# SIGNALS - RECALCULO AUTOMÁTICO DE STOCK DESDE EL PANEL ADMIN
# =========================================================================

@receiver([post_save, post_delete], sender=BodegaStock)
def actualizar_stock_global_producto(sender, instance, **kwargs):
    """
    Cada vez que se añade, modifica o elimina un lote físico en BodegaStock,
    se calcula la sumatoria real y se estampa en el stock_total del Producto.
    """
    producto = instance.producto
    if producto:
        # Sumamos las existencias de todas las bodegas de este producto
        total = BodegaStock.objects.filter(producto=producto).aggregate(total_stock=Sum('stock'))['total_stock'] or 0
        # Guardamos directamente en la columna física
        Producto.objects.filter(id=producto.id).update(stock_total=total)


# =========================================================================
# SIGNALS - LIMPIEZA TOTAL AUTOMÁTICA DEL HISTORIAL ADM
# =========================================================================

@receiver([post_save, post_delete], sender=Producto)
def limpiar_historial_admin_total(sender, instance, **kwargs):
    try:
        # Borra instantáneamente cualquier acción asociada al ID de este producto
        LogEntry.objects.filter(object_id=str(instance.id)).delete()
    except Exception:
        pass