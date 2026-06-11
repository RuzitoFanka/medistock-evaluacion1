from django.db import models
from django.core.validators import MinValueValidator  # 🛡️ Protección contra valores negativos
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
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

    def __str__(self):
        return f"{self.codigo_producto} - {self.nombre}"

    @property
    def stock_total(self):
        # Suma automática del stock en todas las bodegas
        return sum(item.stock for item in self.existencias.all())

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
# SIGNALS - LIMPIEZA TOTAL AUTOMÁTICA DEL HISTORIAL ADM
# =========================================================================

@receiver([post_save, post_delete], sender=Producto)
def limpiar_historial_admin_total(sender, instance, **kwargs):
  
  
    try:
        # Borra instantáneamente cualquier acción asociada al ID de este producto
        LogEntry.objects.filter(object_id=str(instance.id)).delete()
    except Exception:
        pass