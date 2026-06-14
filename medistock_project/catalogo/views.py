from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from transbank.webpay.webpay_plus.transaction import Transaction
from .models import Producto, BodegaStock
import json
import random

# =========================================================================
# VISTAS DE LAS APIs REST FRAMEWORK (CON TRANSBANK INTEGRADO)
# =========================================================================

class ConsultaStockAPIView(APIView):
    """ API para consultar las existencias de un producto mediante su código """
    def get(self, request, codigo_producto):
        try:
            producto = Producto.objects.get(codigo_producto=codigo_producto)
            return Response({'codigo': producto.codigo_producto, 'stock': producto.stock_total}, status=status.HTTP_200_OK)
        except Producto.DoesNotExist:
            return Response({'error': 'Producto no encontrado'}, status=status.HTTP_404_NOT_FOUND)


class ProcesarPagoAPIView(APIView):
    """ API que genera el token seguro y la URL de redirección a Transbank """
    def post(self, request):
        try:
            data = request.data
            items = data.get('items', [])
            
            if not items:
                return Response({'error': 'No hay insumos en el pedido'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Calcular el monto total acumulado del carrito
            monto_total = sum(float(item['precio']) * int(item['cantidad']) for item in items)
            
            # Crear identificadores únicos requeridos por la pasarela
            buy_order = f"O-{random.randint(100000, 999999)}"
            session_id = f"S-{random.randint(100000, 999999)}"
            
            # URL de retorno al finalizar el flujo de Webpay
            return_url = "http://127.0.0.1:8000/" 

            # Transacción en el ambiente de Webpay Plus
            tx = Transaction()
            response = tx.create(buy_order, session_id, monto_total, return_url)
            
            return Response({
                'status': 'ok',
                'url': response['url'],
                'token': response['token']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerarTrackingAPIView(APIView):
    """ API auxiliar para generación de números de guías logísticas """
    def post(self, request):
        return Response({'tracking_id': 'MS-123456'}, status=status.HTTP_200_OK)


# =========================================================================
# VISTAS DE LAS PÁGINAS WEB (TEMPLATES HTML)
# =========================================================================

def vista_tienda(request):
    """ Renderiza el catálogo principal de insumos médicos """
    productos = Producto.objects.all()
    return render(request, 'catalogo/tienda.html', {'productos': productos})


def resumen_orden_view(request):
    """ Muestra la pantalla resumen estructurada de la orden médica """
    return render(request, 'catalogo/resumen_orden.html')


def login_view(request):
    """ Módulo de Autenticación para operadores de MediStock """
    if request.method == 'POST':
        usuario = request.POST.get('username')
        clave = request.POST.get('password')
        
        # Validación nativa contra la base de datos de usuarios de Django
        user = authenticate(request, username=usuario, password=clave)
        
        if user is not None:
            login(request, user)
            return redirect('pantalla-tienda')  # Redirección exitosa al catálogo
        else:
            return render(request, 'catalogo/login.html', {
                'error_message': 'Credenciales inválidas o usuario no autorizado.'
            })
            
    return render(request, 'catalogo/login.html')


def procesar_compra_view(request):
    """ Rebaja de manera lógica el inventario remanente de las bodegas físicas """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('items', [])

            for item in items:
                producto_id = item['id']
                cantidad_comprada = int(item['cantidad'])
                producto = Producto.objects.get(id=producto_id)
                if producto.stock_total < cantidad_comprada:
                    return JsonResponse({'status': 'error', 'message': f"El insumo '{producto.nombre}' no cuenta con stock suficiente."})

            for item in items:
                producto_id = item['id']
                cantidad_comprada = int(item['cantidad'])
                existencias_bodega = BodegaStock.objects.filter(producto_id=producto_id).order_by('-stock')
                
                por_descontar = cantidad_comprada
                for registro in existencias_bodega:
                    if registro.stock >= por_descontar:
                        registro.stock -= por_descontar
                        registro.save()
                        break
                    else:
                        por_descontar -= registro.stock
                        registro.stock = 0
                        registro.save()

            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=400)


# =========================================================================
# 📉 ENLACE DE COMPRA DESDE EL CARRITO (REBAJA STOCK GLOBAL Y EN BODEGAS)
# =========================================================================
def procesar_pedido(request):
    """ Recibe el carrito, valida existencias, y descuenta tanto el stock global como por bodega """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items_pedido = data.get('items', [])
            
            if not items_pedido:
                return JsonResponse({'error': 'No hay artículos en el pedido.'}, status=400)
            
            # Bloque transaccional: Si algo falla con un producto, no se guarda nada (integridad total)
            with transaction.atomic():
                for item in items_pedido:
                    producto_id = item.get('id')
                    cantidad_comprada = int(item.get('cantidad'))
                    
                    # 1️⃣ Buscamos el Producto y bloqueamos la fila para evitar concurrencia
                    producto = Producto.objects.select_for_update().get(id=producto_id)
                    
                    # Validación estricta en servidor antes de procesar el descuento
                    if producto.stock_total < cantidad_comprada:
                        return JsonResponse({
                            'error': f'Stock insuficiente para "{producto.nombre}". Disponible en sistema: {producto.stock_total} un.'
                        }, status=400)
                    
                    # 2️⃣ DESCUENTO EN BODEGAS FÍSICAS (BodegaStock) - De mayor a menor stock
                    existencias_bodega = BodegaStock.objects.filter(producto_id=producto_id).order_by('-stock')
                    por_descontar = cantidad_comprada
                    
                    for registro in existencias_bodega:
                        if registro.stock >= por_descontar:
                            registro.stock -= por_descontar
                            registro.save()
                            por_descontar = 0
                            break
                        else:
                            por_descontar -= registro.stock
                            registro.stock = 0
                            registro.save()
                    
                    if por_descontar > 0:
                        raise Exception(f"Inconsistencia: No se pudo descontar el total de bodegas para {producto.nombre}")

                    # 3️⃣ DESCUENTO EN EL STOCK TOTAL GLOBAL DEL PRODUCTO
                    producto.stock_total -= cantidad_comprada
                    producto.save()
                    
            return JsonResponse({'message': 'Orden procesada con éxito. El stock global y de bodegas ha sido rebajado.'}, status=200)
            
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Uno de los insumos seleccionados no existe en el catálogo.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'Error en el servidor de inventario: {str(e)}'}, status=500)
            
    return JsonResponse({'error': 'Método inválido.'}, status=405)