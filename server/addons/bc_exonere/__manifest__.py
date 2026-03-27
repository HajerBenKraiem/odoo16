# -*- coding: utf-8 -*-
{
    'name': "bc_exonere",

    'summary': """
       Gestion des factures exonérées de TVA et export conforme aux normes fiscales tunisiennes""",

    'description': """
       Module de gestion des factures exonérées de TVA sous Odoo.

Fonctionnalités principales :
- Gestion des informations d’exonération (numéro, dates)
- Contrôle automatique de la TVA pour les clients exonérés
- Vérification de la validité des dates d’exonération
- Génération d’un fichier texte (EF / DF / TF) conforme aux exigences fiscales tunisiennes
- Export téléchargeable directement depuis la facture

Ce module permet d’assurer la conformité réglementaire des entreprises travaillant avec des clients exonérés.
    """,

    'author': "OumaimaAbida & HajerBenKraiem",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'account', 'sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/data.xml',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
