"""Shared analysis constants."""

CARBON_EXCHANGE_IDS = ("Ex_glyc", "Ex_glc_D", "Ex_meoh")
OBJECTIVE_RANK_TOLERANCE = 1e-9
FVA_FIXED_TOLERANCE = 1e-9
FVA_NARROW_TOLERANCE = 1e-4

FVA_SCOPE_OPTIONS = {
    "open_exchange": "当前开放交换反应",
    "all_exchange": "全部交换反应",
    "amino_acid_supply": "氨基酸供给代表反应",
}

AMINO_ACID_METABOLITE_IDS = {
    "ala_L_c": "Ala / 丙氨酸",
    "arg_L_c": "Arg / 精氨酸",
    "asn_L_c": "Asn / 天冬酰胺",
    "asp_L_c": "Asp / 天冬氨酸",
    "cys_L_c": "Cys / 半胱氨酸",
    "gln_L_c": "Gln / 谷氨酰胺",
    "glu_L_c": "Glu / 谷氨酸",
    "gly_c": "Gly / 甘氨酸",
    "his_L_c": "His / 组氨酸",
    "ile_L_c": "Ile / 异亮氨酸",
    "leu_L_c": "Leu / 亮氨酸",
    "lys_L_c": "Lys / 赖氨酸",
    "met_L_c": "Met / 甲硫氨酸",
    "phe_L_c": "Phe / 苯丙氨酸",
    "pro_L_c": "Pro / 脯氨酸",
    "ser_L_c": "Ser / 丝氨酸",
    "thr_L_c": "Thr / 苏氨酸",
    "trp_L_c": "Trp / 色氨酸",
    "tyr_L_c": "Tyr / 酪氨酸",
    "val_L_c": "Val / 缬氨酸",
}

EXCHANGE_CHINESE_NAMES = {
    "Ex_btn": "生物素",
    "Ex_fe2": "亚铁离子",
    "Ex_glyc": "甘油",
    "Ex_h": "质子",
    "Ex_h2o": "水",
    "Ex_k": "钾离子",
    "Ex_nh4": "铵离子/氮源",
    "Ex_o2": "氧气",
    "Ex_pi": "磷酸盐",
    "Ex_so4": "硫酸盐",
    "Ex_glc_D": "D-葡萄糖",
    "Ex_meoh": "甲醇",
    "Ex_co2": "二氧化碳",
    "Ex_etoh": "乙醇",
}
