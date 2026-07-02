# -*- coding: utf-8 -*-
#
#################################################################################
# Author      : Weblytic Labs Pvt. Ltd. (<https://store.weblyticlabs.com/>)
# Copyright(c): 2023-Present Weblytic Labs Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
##################################################################################

from odoo import http, fields
from odoo.http import request
from datetime import datetime, time, timedelta
import urllib.request
import urllib.parse
import json
import requests
import logging

_logger = logging.getLogger(__name__)

def geocode_address(street, city, state, country):
    parts = [street, city, state, country]
    query = ", ".join([p for p in parts if p])
    if not query:
        return None
    
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1"
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'OdooFedexDashboard/19.0 (support@weblyticlabs.com)'}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        _logger.warning("Geocoding failed for %s: %s", query, e)
        
    # Fallback to city, state, country to target the correct city if specific street lookup fails
    city_parts = [city, state, country]
    city_query = ", ".join([p for p in city_parts if p])
    if city_query and city_query != query:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(city_query)}&format=json&limit=1"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'OdooFedexDashboard/19.0 (support@weblyticlabs.com)'}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                if data:
                    return float(data[0]['lat']), float(data[0]['lon'])
        except Exception as e:
            _logger.warning("Geocoding fallback failed for %s: %s", city_query, e)
            
    return None

class FedExDashboardController(http.Controller):

    def _get_common_domain(self, date_range, search_query=None):
        domain = [('name', 'not like', 'SHIP-MOCK-%')]
        
        # Search query
        if search_query:
            domain += ['|', '|',
                ('tracking_number', 'ilike', search_query),
                ('partner_id.name', 'ilike', search_query),
                ('sale_id.name', 'ilike', search_query)
            ]
            
        # Date range
        today = fields.Date.today()
        if date_range == 'today':
            domain += [('create_date', '>=', datetime.combine(today, time.min))]
        elif date_range == '7d':
            domain += [('create_date', '>=', datetime.combine(today - timedelta(days=7), time.min))]
        elif date_range == '30d':
            domain += [('create_date', '>=', datetime.combine(today - timedelta(days=30), time.min))]
        elif date_range == 'this_month':
            domain += [('create_date', '>=', datetime.combine(today.replace(day=1), time.min))]
            
        return domain

    @http.route('/dashboard/kpi', type='json', auth='user')
    def get_kpis(self, date_range='all', search_query=None, **kwargs):
        domain = self._get_common_domain(date_range, search_query)
        Shipping = request.env['fedex.shipping']
        
        # Total shipments
        total_shipments = Shipping.search_count(domain)
        
        # Today's shipments
        today_start = datetime.combine(fields.Date.today(), time.min)
        today_shipments = Shipping.search_count([('create_date', '>=', today_start)] + (self._get_common_domain('all', search_query)))
        
        # Labels created
        label_domain = []
        if search_query:
            label_domain += ['|', '|',
                ('tracking_number', 'ilike', search_query),
                ('sale_ids.name', 'ilike', search_query),
                ('sale_ids.partner_id.name', 'ilike', search_query)
            ]
        today_date = fields.Date.today()
        if date_range == 'today':
            label_domain += [('create_date', '>=', datetime.combine(today_date, time.min))]
        elif date_range == '7d':
            label_domain += [('create_date', '>=', datetime.combine(today_date - timedelta(days=7), time.min))]
        elif date_range == '30d':
            label_domain += [('create_date', '>=', datetime.combine(today_date - timedelta(days=30), time.min))]
        elif date_range == 'this_month':
            label_domain += [('create_date', '>=', datetime.combine(today_date.replace(day=1), time.min))]
            
        labels_created = request.env['fedex.label'].search_count(label_domain)
        
        # Delivered shipments
        delivered_shipments = Shipping.search_count([('state', '=', 'shipped')] + domain)
        
        # Shipment Statistics
        res = Shipping.with_context(tz='UTC')._read_group(domain, aggregates=['shipping_charge:sum', 'shipping_charge:avg', 'shipping_charge:max', 'shipping_charge:min'])
        sum_val, avg_val, max_val, min_val = res[0] if res else (0.0, 0.0, 0.0, 0.0)
        
        # Carrier Performance
        # Group by service_name
        perf_res = Shipping.with_context(tz='UTC')._read_group(domain, groupby=['service_name'], aggregates=['__count'])
        carrier_performance = []
        for service_name, count in perf_res:
            if service_name:
                carrier_performance.append({
                    'service': service_name,
                    'count': count
                })
        
        # Add carriers config for testing
        carriers = request.env["delivery.carrier"].search([("delivery_type", "=", "fedex")])
        delivery_carriers_list = []
        for carrier in carriers:
            delivery_carriers_list.append({
                'id': carrier.id,
                'name': carrier.name,
                'fedex_api_key': carrier.fedex_api_key or '',
                'fedex_secret_key': carrier.fedex_secret_key or '',
                'fedex_account': carrier.fedex_account or '',
                'prod_environment': carrier.prod_environment,
                'fedex_base_url': carrier.fedex_base_url or '',
            })

        # Calculate Map Location Data using state and country centroids
        STATE_COORDINATES = {
            'California': {'lat': 36.7783, 'lng': -119.4179},
            'Texas': {'lat': 31.9686, 'lng': -99.9018},
            'New York': {'lat': 40.7128, 'lng': -74.0060},
            'Florida': {'lat': 27.6648, 'lng': -81.5158},
            'Illinois': {'lat': 40.6331, 'lng': -89.3985},
            'Pennsylvania': {'lat': 41.2033, 'lng': -77.1945},
            'Ohio': {'lat': 40.4173, 'lng': -82.9071},
            'Georgia': {'lat': 32.1656, 'lng': -82.9001},
            'North Carolina': {'lat': 35.7596, 'lng': -79.0193},
            'Michigan': {'lat': 44.3148, 'lng': -85.6024},
            'Washington': {'lat': 47.7511, 'lng': -120.7401},
            'Virginia': {'lat': 37.4316, 'lng': -78.6569},
            'Arizona': {'lat': 34.0489, 'lng': -111.0937},
            'Massachusetts': {'lat': 42.4072, 'lng': -71.3824},
            'Ontario': {'lat': 51.2538, 'lng': -85.3232},
            'Quebec': {'lat': 52.9399, 'lng': -73.5491},
            'British Columbia': {'lat': 53.7267, 'lng': -127.6476},
        }

        COUNTRY_COORDINATES = {
            'United States': {'lat': 37.0902, 'lng': -95.7129},
            'Canada': {'lat': 56.1304, 'lng': -106.3468},
            'United Kingdom': {'lat': 55.3781, 'lng': -3.4360},
            'Germany': {'lat': 51.1657, 'lng': 10.4515},
            'France': {'lat': 46.2276, 'lng': 2.2137},
            'India': {'lat': 20.5937, 'lng': 78.9629},
            'China': {'lat': 35.8617, 'lng': 104.1954},
            'Australia': {'lat': -25.2744, 'lng': 133.7751},
            'Brazil': {'lat': -14.2350, 'lng': -51.9253},
        }

        # Query shipments based on domain
        shipments_data = Shipping.search(domain)
        map_data = []
        for idx, s in enumerate(shipments_data):
            # Target the shipping destination address partner rather than billing customer
            partner = s.picking_id.partner_id or s.partner_id
            lat = 0.0
            lng = 0.0
            country = 'United States'
            
            if partner:
                country = partner.country_id.name or 'United States'
                if partner.partner_latitude and partner.partner_longitude and partner.partner_latitude != 0.0:
                    lat = partner.partner_latitude
                    lng = partner.partner_longitude
                else:
                    state_name = partner.state_id.name if partner.state_id else None
                    coords = geocode_address(partner.street, partner.city, state_name, country)
                    if coords:
                        lat, lng = coords
                        try:
                            # Save back to database so we don't geocode again next time!
                            partner.sudo().write({
                                'partner_latitude': lat,
                                'partner_longitude': lng
                            })
                        except Exception as write_err:
                            _logger.warning("Failed to save geocoded coordinates to partner: %s", write_err)
                    else:
                        if state_name and state_name in STATE_COORDINATES:
                            lat = STATE_COORDINATES[state_name]['lat']
                            lng = STATE_COORDINATES[state_name]['lng']
                        elif country in COUNTRY_COORDINATES:
                            lat = COUNTRY_COORDINATES[country]['lat']
                            lng = COUNTRY_COORDINATES[country]['lng']
                        else:
                            lat = COUNTRY_COORDINATES['United States']['lat']
                            lng = COUNTRY_COORDINATES['United States']['lng']
            else:
                lat = COUNTRY_COORDINATES['United States']['lat']
                lng = COUNTRY_COORDINATES['United States']['lng']

            # Retrieve credential detail safely
            carrier = s.carrier_id or request.env['delivery.carrier'].search([('delivery_type', '=', 'fedex')], limit=1)
            account_number = carrier.fedex_account or '12345678'
            
            # Reduce jitter so that pins display within the correct city bounds instead of jumping cities
            jitter_lat = (idx * 0.003) % 0.01 - 0.005
            jitter_lng = (idx * 0.004) % 0.01 - 0.005
            
            map_data.append({
                'country': country,
                'count': 1,
                'lat': lat + jitter_lat,
                'lng': lng + jitter_lng,
                'order_name': s.name or 'Order',
                'account': account_number,
                'balance': f"${s.shipping_charge or 0.0:,.2f}"
            })

        return {
            'kpis': {
                'total_shipments': total_shipments,
                'today_shipments': today_shipments,
                'labels_created': labels_created,
                'delivered_shipments': delivered_shipments,
                'stats': {
                    'total_charges': sum_val or 0.0,
                    'avg_cost': avg_val or 0.0,
                    'highest_cost': max_val or 0.0,
                    'lowest_cost': min_val or 0.0,
                }
            },
            'carrier_performance': carrier_performance,
            'delivery_carriers': delivery_carriers_list,
            'map_data': map_data,
            'is_empty': Shipping.sudo().search_count([]) == 0
        }

    @http.route('/dashboard/chart', type='json', auth='user')
    def get_chart_data(self, date_range='all', search_query=None, **kwargs):
        domain = self._get_common_domain(date_range, search_query)
        Shipping = request.env['fedex.shipping']
        
        today = fields.Date.today()
        # Display shipment count for last 7 days
        dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
        date_strings = [d.strftime('%Y-%m-%d') for d in dates]
        counts = {d_str: 0 for d_str in date_strings}
        
        seven_days_ago = datetime.combine(today - timedelta(days=6), time.min)
        groups = Shipping.with_context(tz='UTC')._read_group(
            domain + [('create_date', '>=', seven_days_ago)],
            groupby=['create_date:day'],
            aggregates=['__count']
        )
        
        for group_date, count in groups:
            if group_date:
                date_str = group_date.strftime('%Y-%m-%d')
                if date_str in counts:
                    counts[date_str] = count
                    
        chart_data = []
        for d_str in date_strings:
            chart_data.append({
                'date': d_str,
                'count': counts[d_str]
            })
            
        return chart_data

    @http.route('/dashboard/latest_shipments', type='json', auth='user')
    def get_latest_shipments(self, date_range='all', search_query=None, **kwargs):
        domain = self._get_common_domain(date_range, search_query)
        shipments = request.env['fedex.shipping'].search_read(
            domain,
            ['id', 'name', 'tracking_number', 'partner_id', 'carrier_id', 'service_name', 'shipping_charge', 'state', 'create_date'],
            limit=10,
            order='id desc'
        )
        
        # Prefetch partner country and state names for destination display
        partner_ids = list(set(s['partner_id'][0] for s in shipments if s['partner_id']))
        partners = request.env['res.partner'].search_read([('id', 'in', partner_ids)], ['country_id', 'state_id'])
        partner_country_state = {}
        for p in partners:
            country = p['country_id'][1] if p['country_id'] else ''
            state = p['state_id'][1] if p['state_id'] else ''
            parts = [state, country]
            partner_country_state[p['id']] = ", ".join([x for x in parts if x]) or 'United States'
        
        latest = []
        for s in shipments:
            pid = s['partner_id'][0] if s['partner_id'] else False
            destination = partner_country_state.get(pid, 'United States')
            latest.append({
                'id': s['id'],
                'name': s['name'] or f"SHIP-{s['id']}",
                'tracking_number': s['tracking_number'] or 'N/A',
                'customer': s['partner_id'][1] if s['partner_id'] else 'N/A',
                'carrier': s['carrier_id'][1] if s['carrier_id'] else 'N/A',
                'service_name': s['service_name'] or 'N/A',
                'shipping_charge': s['shipping_charge'] or 0.0,
                'state': s['state'],
                'create_date': s['create_date'].strftime('%Y-%m-%d') if s['create_date'] else 'N/A',
                'destination': destination,
            })
        return latest

    @http.route('/dashboard/latest_labels', type='json', auth='user')
    def get_latest_labels(self, search_query=None, **kwargs):
        label_domain = []
        if search_query:
            label_domain = ['|', '|',
                ('tracking_number', 'ilike', search_query),
                ('sale_ids.name', 'ilike', search_query),
                ('picking_id.name', 'ilike', search_query)
            ]
            
        labels = request.env['fedex.label'].search_read(
            label_domain,
            ['id', 'tracking_number', 'sale_ids', 'picking_id', 'service_type', 'create_date', 'attachment_id'],
            limit=10,
            order='id desc'
        )
        
        latest = []
        for l in labels:
            latest.append({
                'id': l['id'],
                'tracking_number': l['tracking_number'] or 'N/A',
                'sale_order': l['sale_ids'][1] if l['sale_ids'] else 'N/A',
                'picking': l['picking_id'][1] if l['picking_id'] else 'N/A',
                'service_type': l['service_type'] or 'N/A',
                'create_date': l['create_date'].strftime('%Y-%m-%d %H:%M') if l['create_date'] else 'N/A',
                'attachment_id': l['attachment_id'][0] if l['attachment_id'] else False,
            })
        return latest

    @http.route('/dashboard/activity', type='json', auth='user')
    def get_activity_feed(self, search_query=None, **kwargs):
        # Fetch latest shipments & labels
        shipments = request.env['fedex.shipping'].search_read(
            [('name', 'not like', 'SHIP-MOCK-%')],
            ['name', 'state', 'create_date', 'write_date'],
            limit=10,
            order='write_date desc'
        )
        labels = request.env['fedex.label'].search_read(
            ['|', ('sale_ids', '=', False), ('sale_ids.name', 'not like', 'SHIP-MOCK-%')],
            ['tracking_number', 'create_date'],
            limit=10,
            order='create_date desc'
        )
        
        activities = []
        for s in shipments:
            activities.append({
                'title': 'Shipment Created',
                'description': f"Shipment '{s['name']}' has been created in Draft state.",
                'date': s['create_date'],
                'icon': 'fa-plus-circle',
                'color': 'text-primary'
            })
            if s['state'] == 'cancel':
                activities.append({
                    'title': 'Shipment Cancelled',
                    'description': f"Shipment '{s['name']}' has been cancelled.",
                    'date': s['write_date'],
                    'icon': 'fa-times-circle',
                    'color': 'text-danger'
                })
            elif s['state'] == 'shipped':
                activities.append({
                    'title': 'Shipment Shipped',
                    'description': f"Shipment '{s['name']}' has been marked as Shipped.",
                    'date': s['write_date'],
                    'icon': 'fa-check-circle',
                    'color': 'text-success'
                })
                
        for l in labels:
            activities.append({
                'title': 'Label Generated',
                'description': f"FedEx label generated. Tracking Number: {l['tracking_number']}.",
                'date': l['create_date'],
                'icon': 'fa-print',
                'color': 'text-warning'
            })
            
        activities.sort(key=lambda x: x['date'], reverse=True)
        activities = activities[:10]
        
        for act in activities:
            act['date'] = act['date'].strftime('%Y-%m-%d %H:%M')
            
        return activities

    @http.route('/dashboard/status_chart', type='json', auth='user')
    def get_status_chart_data(self, date_range='all', search_query=None, **kwargs):
        domain = self._get_common_domain(date_range, search_query)
        groups = request.env['fedex.shipping'].with_context(tz='UTC')._read_group(
            domain,
            groupby=['state'],
            aggregates=['__count']
        )
        
        status_counts = {'draft': 0, 'shipped': 0, 'cancel': 0}
        for state, count in groups:
            if state in status_counts:
                status_counts[state] = count
                
        return [
            {'status': 'Draft', 'count': status_counts['draft']},
            {'status': 'Shipped', 'count': status_counts['shipped']},
            {'status': 'Cancelled', 'count': status_counts['cancel']}
        ]

    @http.route('/dashboard/seed_data', type='json', auth='user')
    def seed_data(self, **kwargs):
        request.env['fedex.shipping'].action_seed_mock_data()
        return {'success': True}

    @http.route('/dashboard/get_sale_orders', type='json', auth='user')
    def get_sale_orders(self, **kwargs):
        orders = request.env['sale.order'].search([
            ('partner_shipping_id', '!=', False)
        ], order='id desc', limit=20)
        
        result = []
        for order in orders:
            picking = order.picking_ids[:1]
            if picking:
                weight = sum(
                    move.product_id.weight * move.product_uom_qty
                    for move in picking.move_ids
                )
            else:
                weight = sum(
                    line.product_id.weight * line.product_uom_qty
                    for line in order.order_line
                )
            weight = max(weight, 0.1)

            result.append({
                'id': order.id,
                'name': order.name,
                'partner_name': order.partner_id.name,
                'shipping_city': order.partner_shipping_id.city or '',
                'shipping_zip': order.partner_shipping_id.zip or '',
                'shipping_country': order.partner_shipping_id.country_id.name or '',
                'shipping_country_code': order.partner_shipping_id.country_id.code or '',
                'weight': weight,
                'amount_total': order.amount_total,
                'currency': order.currency_id.name,
                'date_order': order.date_order.strftime('%Y-%m-%d') if order.date_order else '',
                'state': order.state,
                'selected_service': order.fedex_service_name or '',
                'selected_amount': order.fedex_rate_amount or 0.0,
            })
        return result

    @http.route('/dashboard/get_rates_for_order', type='json', auth='user')
    def get_rates_for_order(self, order_id, **kwargs):
        order = request.env['sale.order'].browse(int(order_id))
        if not order.exists():
            return {'success': False, 'error': 'Sale Order not found.'}
            
        carrier = request.env['delivery.carrier'].search([('delivery_type', '=', 'fedex')], limit=1)
        if not carrier:
            return {
                'success': False,
                'error': 'No FedEx carrier configured in Odoo. Please set one up first.'
            }

        try:
            token = carrier.fedex_auth_token()
            url = f"{carrier.fedex_base_url}/rate/v1/rates/quotes"
            
            picking = order.picking_ids[:1]
            if picking:
                weight = sum(
                    move.product_id.weight * move.product_uom_qty
                    for move in picking.move_ids
                )
            else:
                weight = sum(
                    line.product_id.weight * line.product_uom_qty
                    for line in order.order_line
                )
            weight = max(weight, 0.1)

            payload = {
                "accountNumber": {
                    "value": str(carrier.fedex_account)
                },
                "requestedShipment": {
                    "shipDateStamp": fields.Date.today().strftime("%Y-%m-%d"),
                    "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
                    "rateRequestType": ["LIST"],
                    "shipper": {
                        "address": {
                            "countryCode": order.company_id.country_id.code or "US",
                            "postalCode": order.company_id.zip or "",
                        }
                    },
                    "recipient": {
                        "address": {
                            "countryCode": order.partner_shipping_id.country_id.code or "US",
                            "postalCode": order.partner_shipping_id.zip or "",
                        }
                    },
                    "requestedPackageLineItems": [
                        {
                            "weight": {
                                "units": "LB",
                                "value": weight
                            }
                        }
                    ]
                }
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, json=payload, headers=headers, timeout=15)
            data = response.json()

            if response.status_code >= 400:
                err_msg = data.get("errors", [{}])[0].get("message", "FedEx Rate Request Failed")
                return {
                    'success': False,
                    'error': err_msg
                }

            rates = []
            for service in data.get("output", {}).get("rateReplyDetails", []):
                rate_detail = service.get("ratedShipmentDetails", [{}])[0]
                rates.append({
                    "service_name": service.get("serviceName") or service.get("serviceType"),
                    "service_code": service.get("serviceType"),
                    "amount": rate_detail.get("totalNetCharge", 0.0),
                    "currency": rate_detail.get("currency") or order.currency_id.name or "USD",
                })

            rates = sorted(rates, key=lambda r: r['amount'])
            return {
                'success': True,
                'rates': rates
            }
        except Exception as e:
            _logger.exception("Error calling FedEx Rate API: %s", str(e))
            return {
                'success': False,
                'error': f"Error calling FedEx Rate API: {str(e)}"
            }

    @http.route('/dashboard/select_rate_for_order', type='json', auth='user')
    def select_rate_for_order(self, order_id, service_code, service_name, amount, **kwargs):
        order = request.env['sale.order'].browse(int(order_id))
        if not order.exists():
            return {'success': False, 'error': 'Sale Order not found.'}
            
        carrier = request.env['delivery.carrier'].search([('delivery_type', '=', 'fedex')], limit=1)
        if not carrier:
            return {'success': False, 'error': 'No FedEx carrier configured.'}

        try:
            # Update delivery line
            order.set_delivery_line(carrier, float(amount))
            
            delivery_line = order.order_line.filtered(lambda l: l.is_delivery)
            if delivery_line:
                delivery_line.name = f"{carrier.name}\n{service_name}"
                
            order.write({
                'fedex_service_code': service_code,
                'fedex_service_name': service_name,
                'fedex_rate_amount': float(amount),
            })
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/dashboard/get_packages', type='json', auth='user')
    def get_packages(self, **kwargs):
        packages = request.env['stock.package.type'].search([
            ('fedex_packaging_type', '!=', False)
        ])
        result = []
        for pkg in packages:
            selection_dict = dict(pkg._fields['fedex_packaging_type'].selection)
            result.append({
                'id': pkg.id,
                'name': pkg.name,
                'fedex_packaging_type': selection_dict.get(pkg.fedex_packaging_type) or pkg.fedex_packaging_type,
                'length': pkg.packaging_length,
                'width': pkg.width,
                'height': pkg.height,
                'base_weight': pkg.base_weight,
                'max_weight': pkg.max_weight,
            })
        return result

    @http.route('/dashboard/get_all_shipments', type='json', auth='user')
    def get_all_shipments(self, **kwargs):
        shipments = request.env['fedex.shipping'].search([])
        result = []
        for s in shipments:
            partner = s.partner_id
            country = partner.country_id.name or 'United States'
            country_code = partner.country_id.code or 'US'
            result.append({
                'id': s.id,
                'name': s.name or f"SHIP-{s.id}",
                'partner_id': partner.id or False,
                'tracking_number': s.tracking_number or 'N/A',
                'customer': partner.name or 'N/A',
                'carrier': s.carrier_id.name or 'N/A',
                'service_name': s.service_name or 'N/A',
                'shipping_charge': s.shipping_charge or 0.0,
                'state': s.state,
                'date': s.shipment_date.strftime('%Y-%m-%d %H:%M') if s.shipment_date else s.create_date.strftime('%Y-%m-%d %H:%M'),
                'country': country,
                'country_code': country_code,
            })
        return result
