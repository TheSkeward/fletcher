from datetime import datetime, timedelta
from PIL import Image, ImageOps
from sys import exc_info
import asyncio
import aiohttp
import codecs
import discord
import hashlib
import io
import logging
import math
import messagefuncs
import netcode
import random
import shortuuid
import textwrap
import ujson
import zalgo.zalgo as zalgo

logger = logging.getLogger("fletcher")

emoji_name_lookup = {
    ":mahjong:": "🀄️",
    ":black_joker:": "🃏",
    ":a:": "🅰️",
    ":b:": "🅱️",
    ":o2:": "🅾️",
    ":parking:": "🅿️",
    ":ab:": "🆎",
    ":cl:": "🆑",
    ":cool:": "🆒",
    ":free:": "🆓",
    ":id:": "🆔",
    ":new:": "🆕",
    ":ng:": "🆖",
    ":ok:": "🆗",
    ":sos:": "🆘",
    ":up:": "🆙",
    ":vs:": "🆚",
    ":flag_ac:": "🇦🇨",
    ":flag_ad:": "🇦🇩",
    ":flag_ae:": "🇦🇪",
    ":flag_af:": "🇦🇫",
    ":flag_ag:": "🇦🇬",
    ":flag_ai:": "🇦🇮",
    ":flag_al:": "🇦🇱",
    ":flag_am:": "🇦🇲",
    ":flag_ao:": "🇦🇴",
    ":flag_aq:": "🇦🇶",
    ":flag_ar:": "🇦🇷",
    ":flag_as:": "🇦🇸",
    ":flag_at:": "🇦🇹",
    ":flag_au:": "🇦🇺",
    ":flag_aw:": "🇦🇼",
    ":flag_ax:": "🇦🇽",
    ":flag_az:": "🇦🇿",
    ":regional_indicator_a:": "🇦",
    ":flag_ba:": "🇧🇦",
    ":flag_bb:": "🇧🇧",
    ":flag_bd:": "🇧🇩",
    ":flag_be:": "🇧🇪",
    ":flag_bf:": "🇧🇫",
    ":flag_bg:": "🇧🇬",
    ":flag_bh:": "🇧🇭",
    ":flag_bi:": "🇧🇮",
    ":flag_bj:": "🇧🇯",
    ":flag_bl:": "🇧🇱",
    ":flag_bm:": "🇧🇲",
    ":flag_bn:": "🇧🇳",
    ":flag_bo:": "🇧🇴",
    ":flag_bq:": "🇧🇶",
    ":flag_br:": "🇧🇷",
    ":flag_bs:": "🇧🇸",
    ":flag_bt:": "🇧🇹",
    ":flag_bv:": "🇧🇻",
    ":flag_bw:": "🇧🇼",
    ":flag_by:": "🇧🇾",
    ":flag_bz:": "🇧🇿",
    ":regional_indicator_b:": "🇧",
    ":flag_ca:": "🇨🇦",
    ":flag_cc:": "🇨🇨",
    ":flag_cd:": "🇨🇩",
    ":flag_cf:": "🇨🇫",
    ":flag_cg:": "🇨🇬",
    ":flag_ch:": "🇨🇭",
    ":flag_ci:": "🇨🇮",
    ":flag_ck:": "🇨🇰",
    ":flag_cl:": "🇨🇱",
    ":flag_cm:": "🇨🇲",
    ":flag_cn:": "🇨🇳",
    ":flag_co:": "🇨🇴",
    ":flag_cp:": "🇨🇵",
    ":flag_cr:": "🇨🇷",
    ":flag_cu:": "🇨🇺",
    ":flag_cv:": "🇨🇻",
    ":flag_cw:": "🇨🇼",
    ":flag_cx:": "🇨🇽",
    ":flag_cy:": "🇨🇾",
    ":flag_cz:": "🇨🇿",
    ":regional_indicator_c:": "🇨",
    ":flag_de:": "🇩🇪",
    ":flag_dg:": "🇩🇬",
    ":flag_dj:": "🇩🇯",
    ":flag_dk:": "🇩🇰",
    ":flag_dm:": "🇩🇲",
    ":flag_do:": "🇩🇴",
    ":flag_dz:": "🇩🇿",
    ":regional_indicator_d:": "🇩",
    ":flag_ea:": "🇪🇦",
    ":flag_ec:": "🇪🇨",
    ":flag_ee:": "🇪🇪",
    ":flag_eg:": "🇪🇬",
    ":flag_eh:": "🇪🇭",
    ":flag_er:": "🇪🇷",
    ":flag_es:": "🇪🇸",
    ":flag_et:": "🇪🇹",
    ":flag_eu:": "🇪🇺",
    ":regional_indicator_e:": "🇪",
    ":flag_fi:": "🇫🇮",
    ":flag_fj:": "🇫🇯",
    ":flag_fk:": "🇫🇰",
    ":flag_fm:": "🇫🇲",
    ":flag_fo:": "🇫🇴",
    ":flag_fr:": "🇫🇷",
    ":regional_indicator_f:": "🇫",
    ":flag_ga:": "🇬🇦",
    ":flag_gb:": "🇬🇧",
    ":flag_gd:": "🇬🇩",
    ":flag_ge:": "🇬🇪",
    ":flag_gf:": "🇬🇫",
    ":flag_gg:": "🇬🇬",
    ":flag_gh:": "🇬🇭",
    ":flag_gi:": "🇬🇮",
    ":flag_gl:": "🇬🇱",
    ":flag_gm:": "🇬🇲",
    ":flag_gn:": "🇬🇳",
    ":flag_gp:": "🇬🇵",
    ":flag_gq:": "🇬🇶",
    ":flag_gr:": "🇬🇷",
    ":flag_gs:": "🇬🇸",
    ":flag_gt:": "🇬🇹",
    ":flag_gu:": "🇬🇺",
    ":flag_gw:": "🇬🇼",
    ":flag_gy:": "🇬🇾",
    ":regional_indicator_g:": "🇬",
    ":flag_hk:": "🇭🇰",
    ":flag_hm:": "🇭🇲",
    ":flag_hn:": "🇭🇳",
    ":flag_hr:": "🇭🇷",
    ":flag_ht:": "🇭🇹",
    ":flag_hu:": "🇭🇺",
    ":regional_indicator_h:": "🇭",
    ":flag_ic:": "🇮🇨",
    ":flag_id:": "🇮🇩",
    ":flag_ie:": "🇮🇪",
    ":flag_il:": "🇮🇱",
    ":flag_im:": "🇮🇲",
    ":flag_in:": "🇮🇳",
    ":flag_io:": "🇮🇴",
    ":flag_iq:": "🇮🇶",
    ":flag_ir:": "🇮🇷",
    ":flag_is:": "🇮🇸",
    ":flag_it:": "🇮🇹",
    ":regional_indicator_i:": "🇮",
    ":flag_je:": "🇯🇪",
    ":flag_jm:": "🇯🇲",
    ":flag_jo:": "🇯🇴",
    ":flag_jp:": "🇯🇵",
    ":regional_indicator_j:": "🇯",
    ":flag_ke:": "🇰🇪",
    ":flag_kg:": "🇰🇬",
    ":flag_kh:": "🇰🇭",
    ":flag_ki:": "🇰🇮",
    ":flag_km:": "🇰🇲",
    ":flag_kn:": "🇰🇳",
    ":flag_kp:": "🇰🇵",
    ":flag_kr:": "🇰🇷",
    ":flag_kw:": "🇰🇼",
    ":flag_ky:": "🇰🇾",
    ":flag_kz:": "🇰🇿",
    ":regional_indicator_k:": "🇰",
    ":flag_la:": "🇱🇦",
    ":flag_lb:": "🇱🇧",
    ":flag_lc:": "🇱🇨",
    ":flag_li:": "🇱🇮",
    ":flag_lk:": "🇱🇰",
    ":flag_lr:": "🇱🇷",
    ":flag_ls:": "🇱🇸",
    ":flag_lt:": "🇱🇹",
    ":flag_lu:": "🇱🇺",
    ":flag_lv:": "🇱🇻",
    ":flag_ly:": "🇱🇾",
    ":regional_indicator_l:": "🇱",
    ":flag_ma:": "🇲🇦",
    ":flag_mc:": "🇲🇨",
    ":flag_md:": "🇲🇩",
    ":flag_me:": "🇲🇪",
    ":flag_mf:": "🇲🇫",
    ":flag_mg:": "🇲🇬",
    ":flag_mh:": "🇲🇭",
    ":flag_mk:": "🇲🇰",
    ":flag_ml:": "🇲🇱",
    ":flag_mm:": "🇲🇲",
    ":flag_mn:": "🇲🇳",
    ":flag_mo:": "🇲🇴",
    ":flag_mp:": "🇲🇵",
    ":flag_mq:": "🇲🇶",
    ":flag_mr:": "🇲🇷",
    ":flag_ms:": "🇲🇸",
    ":flag_mt:": "🇲🇹",
    ":flag_mu:": "🇲🇺",
    ":flag_mv:": "🇲🇻",
    ":flag_mw:": "🇲🇼",
    ":flag_mx:": "🇲🇽",
    ":flag_my:": "🇲🇾",
    ":flag_mz:": "🇲🇿",
    ":regional_indicator_m:": "🇲",
    ":flag_na:": "🇳🇦",
    ":flag_nc:": "🇳🇨",
    ":flag_ne:": "🇳🇪",
    ":flag_nf:": "🇳🇫",
    ":flag_ng:": "🇳🇬",
    ":flag_ni:": "🇳🇮",
    ":flag_nl:": "🇳🇱",
    ":flag_no:": "🇳🇴",
    ":flag_np:": "🇳🇵",
    ":flag_nr:": "🇳🇷",
    ":flag_nu:": "🇳🇺",
    ":flag_nz:": "🇳🇿",
    ":regional_indicator_n:": "🇳",
    ":flag_om:": "🇴🇲",
    ":regional_indicator_o:": "🇴",
    ":flag_pa:": "🇵🇦",
    ":flag_pe:": "🇵🇪",
    ":flag_pf:": "🇵🇫",
    ":flag_pg:": "🇵🇬",
    ":flag_ph:": "🇵🇭",
    ":flag_pk:": "🇵🇰",
    ":flag_pl:": "🇵🇱",
    ":flag_pm:": "🇵🇲",
    ":flag_pn:": "🇵🇳",
    ":flag_pr:": "🇵🇷",
    ":flag_ps:": "🇵🇸",
    ":flag_pt:": "🇵🇹",
    ":flag_pw:": "🇵🇼",
    ":flag_py:": "🇵🇾",
    ":regional_indicator_p:": "🇵",
    ":flag_qa:": "🇶🇦",
    ":regional_indicator_q:": "🇶",
    ":flag_re:": "🇷🇪",
    ":flag_ro:": "🇷🇴",
    ":flag_rs:": "🇷🇸",
    ":flag_ru:": "🇷🇺",
    ":flag_rw:": "🇷🇼",
    ":regional_indicator_r:": "🇷",
    ":flag_sa:": "🇸🇦",
    ":flag_sb:": "🇸🇧",
    ":flag_sc:": "🇸🇨",
    ":flag_sd:": "🇸🇩",
    ":flag_se:": "🇸🇪",
    ":flag_sg:": "🇸🇬",
    ":flag_sh:": "🇸🇭",
    ":flag_si:": "🇸🇮",
    ":flag_sj:": "🇸🇯",
    ":flag_sk:": "🇸🇰",
    ":flag_sl:": "🇸🇱",
    ":flag_sm:": "🇸🇲",
    ":flag_sn:": "🇸🇳",
    ":flag_so:": "🇸🇴",
    ":flag_sr:": "🇸🇷",
    ":flag_ss:": "🇸🇸",
    ":flag_st:": "🇸🇹",
    ":flag_sv:": "🇸🇻",
    ":flag_sx:": "🇸🇽",
    ":flag_sy:": "🇸🇾",
    ":flag_sz:": "🇸🇿",
    ":regional_indicator_s:": "🇸",
    ":flag_ta:": "🇹🇦",
    ":flag_tc:": "🇹🇨",
    ":flag_td:": "🇹🇩",
    ":flag_tf:": "🇹🇫",
    ":flag_tg:": "🇹🇬",
    ":flag_th:": "🇹🇭",
    ":flag_tj:": "🇹🇯",
    ":flag_tk:": "🇹🇰",
    ":flag_tl:": "🇹🇱",
    ":flag_tm:": "🇹🇲",
    ":flag_tn:": "🇹🇳",
    ":flag_to:": "🇹🇴",
    ":flag_tr:": "🇹🇷",
    ":flag_tt:": "🇹🇹",
    ":flag_tv:": "🇹🇻",
    ":flag_tw:": "🇹🇼",
    ":flag_tz:": "🇹🇿",
    ":regional_indicator_t:": "🇹",
    ":flag_ua:": "🇺🇦",
    ":flag_ug:": "🇺🇬",
    ":flag_um:": "🇺🇲",
    ":regional_indicator_u::regional_indicator_n:": "🇺🇳",
    ":flag_us:": "🇺🇸",
    ":flag_uy:": "🇺🇾",
    ":flag_uz:": "🇺🇿",
    ":regional_indicator_u:": "🇺",
    ":flag_va:": "🇻🇦",
    ":flag_vc:": "🇻🇨",
    ":flag_ve:": "🇻🇪",
    ":flag_vg:": "🇻🇬",
    ":flag_vi:": "🇻🇮",
    ":flag_vn:": "🇻🇳",
    ":flag_vu:": "🇻🇺",
    ":regional_indicator_v:": "🇻",
    ":flag_wf:": "🇼🇫",
    ":flag_ws:": "🇼🇸",
    ":regional_indicator_w:": "🇼",
    ":flag_xk:": "🇽🇰",
    ":regional_indicator_x:": "🇽",
    ":flag_ye:": "🇾🇪",
    ":flag_yt:": "🇾🇹",
    ":regional_indicator_y:": "🇾",
    ":flag_za:": "🇿🇦",
    ":flag_zm:": "🇿🇲",
    ":flag_zw:": "🇿🇼",
    ":regional_indicator_z:": "🇿",
    ":koko:": "🈁",
    ":sa:": "🈂️",
    ":u7121:": "🈚️",
    ":u6307:": "🈯️",
    ":u7981:": "🈲",
    ":u7a7a:": "🈳",
    ":u5408:": "🈴",
    ":u6e80:": "🈵",
    ":u6709:": "🈶",
    ":u6708:": "🈷️",
    ":u7533:": "🈸",
    ":u5272:": "🈹",
    ":u55b6:": "🈺",
    ":ideograph_advantage:": "🉐",
    ":accept:": "🉑",
    ":cyclone:": "🌀",
    ":foggy:": "🌁",
    ":closed_umbrella:": "🌂",
    ":night_with_stars:": "🌃",
    ":sunrise_over_mountains:": "🌄",
    ":sunrise:": "🌅",
    ":city_dusk:": "🌆",
    ":city_sunset:": "🌇",
    ":rainbow:": "🌈",
    ":bridge_at_night:": "🌉",
    ":ocean:": "🌊",
    ":volcano:": "🌋",
    ":milky_way:": "🌌",
    ":earth_africa:": "🌍",
    ":earth_americas:": "🌎",
    ":earth_asia:": "🌏",
    ":globe_with_meridians:": "🌐",
    ":new_moon:": "🌑",
    ":waxing_crescent_moon:": "🌒",
    ":first_quarter_moon:": "🌓",
    ":waxing_gibbous_moon:": "🌔",
    ":full_moon:": "🌕",
    ":waning_gibbous_moon:": "🌖",
    ":last_quarter_moon:": "🌗",
    ":waning_crescent_moon:": "🌘",
    ":crescent_moon:": "🌙",
    ":new_moon_with_face:": "🌚",
    ":first_quarter_moon_with_face:": "🌛",
    ":last_quarter_moon_with_face:": "🌜",
    ":full_moon_with_face:": "🌝",
    ":sun_with_face:": "🌞",
    ":star2:": "🌟",
    ":stars:": "🌠",
    ":thermometer:": "🌡️",
    ":white_sun_small_cloud:": "🌤️",
    ":white_sun_cloud:": "🌥️",
    ":white_sun_rain_cloud:": "🌦️",
    ":cloud_rain:": "🌧️",
    ":cloud_snow:": "🌨️",
    ":cloud_lightning:": "🌩️",
    ":cloud_tornado:": "🌪️",
    ":fog:": "🌫️",
    ":wind_blowing_face:": "🌬️",
    ":hotdog:": "🌭",
    ":taco:": "🌮",
    ":burrito:": "🌯",
    ":chestnut:": "🌰",
    ":seedling:": "🌱",
    ":evergreen_tree:": "🌲",
    ":deciduous_tree:": "🌳",
    ":palm_tree:": "🌴",
    ":cactus:": "🌵",
    ":hot_pepper:": "🌶️",
    ":tulip:": "🌷",
    ":cherry_blossom:": "🌸",
    ":rose:": "🌹",
    ":hibiscus:": "🌺",
    ":sunflower:": "🌻",
    ":blossom:": "🌼",
    ":corn:": "🌽",
    ":ear_of_rice:": "🌾",
    ":herb:": "🌿",
    ":four_leaf_clover:": "🍀",
    ":maple_leaf:": "🍁",
    ":fallen_leaf:": "🍂",
    ":leaves:": "🍃",
    ":mushroom:": "🍄",
    ":tomato:": "🍅",
    ":eggplant:": "🍆",
    ":grapes:": "🍇",
    ":melon:": "🍈",
    ":watermelon:": "🍉",
    ":tangerine:": "🍊",
    ":lemon:": "🍋",
    ":banana:": "🍌",
    ":pineapple:": "🍍",
    ":apple:": "🍎",
    ":green_apple:": "🍏",
    ":pear:": "🍐",
    ":peach:": "🍑",
    ":cherries:": "🍒",
    ":strawberry:": "🍓",
    ":hamburger:": "🍔",
    ":pizza:": "🍕",
    ":meat_on_bone:": "🍖",
    ":poultry_leg:": "🍗",
    ":rice_cracker:": "🍘",
    ":rice_ball:": "🍙",
    ":rice:": "🍚",
    ":curry:": "🍛",
    ":ramen:": "🍜",
    ":spaghetti:": "🍝",
    ":bread:": "🍞",
    ":fries:": "🍟",
    ":sweet_potato:": "🍠",
    ":dango:": "🍡",
    ":oden:": "🍢",
    ":sushi:": "🍣",
    ":fried_shrimp:": "🍤",
    ":fish_cake:": "🍥",
    ":icecream:": "🍦",
    ":shaved_ice:": "🍧",
    ":ice_cream:": "🍨",
    ":doughnut:": "🍩",
    ":cookie:": "🍪",
    ":chocolate_bar:": "🍫",
    ":candy:": "🍬",
    ":lollipop:": "🍭",
    ":custard:": "🍮",
    ":honey_pot:": "🍯",
    ":cake:": "🍰",
    ":bento:": "🍱",
    ":stew:": "🍲",
    ":cooking:": "🍳",
    ":fork_and_knife:": "🍴",
    ":tea:": "🍵",
    ":sake:": "🍶",
    ":wine_glass:": "🍷",
    ":cocktail:": "🍸",
    ":tropical_drink:": "🍹",
    ":beer:": "🍺",
    ":beers:": "🍻",
    ":baby_bottle:": "🍼",
    ":fork_knife_plate:": "🍽️",
    ":champagne:": "🍾",
    ":popcorn:": "🍿",
    ":ribbon:": "🎀",
    ":gift:": "🎁",
    ":birthday:": "🎂",
    ":jack_o_lantern:": "🎃",
    ":christmas_tree:": "🎄",
    ":santa_tone1:": "🎅🏻",
    ":santa_tone2:": "🎅🏼",
    ":santa_tone3:": "🎅🏽",
    ":santa_tone4:": "🎅🏾",
    ":santa_tone5:": "🎅🏿",
    ":santa:": "🎅",
    ":fireworks:": "🎆",
    ":sparkler:": "🎇",
    ":balloon:": "🎈",
    ":tada:": "🎉",
    ":confetti_ball:": "🎊",
    ":tanabata_tree:": "🎋",
    ":crossed_flags:": "🎌",
    ":bamboo:": "🎍",
    ":dolls:": "🎎",
    ":flags:": "🎏",
    ":wind_chime:": "🎐",
    ":rice_scene:": "🎑",
    ":school_satchel:": "🎒",
    ":mortar_board:": "🎓",
    ":military_medal:": "🎖️",
    ":reminder_ribbon:": "🎗️",
    ":microphone2:": "🎙️",
    ":level_slider:": "🎚️",
    ":control_knobs:": "🎛️",
    ":film_frames:": "🎞️",
    ":tickets:": "🎟️",
    ":carousel_horse:": "🎠",
    ":ferris_wheel:": "🎡",
    ":roller_coaster:": "🎢",
    ":fishing_pole_and_fish:": "🎣",
    ":microphone:": "🎤",
    ":movie_camera:": "🎥",
    ":cinema:": "🎦",
    ":headphones:": "🎧",
    ":art:": "🎨",
    ":tophat:": "🎩",
    ":circus_tent:": "🎪",
    ":ticket:": "🎫",
    ":clapper:": "🎬",
    ":performing_arts:": "🎭",
    ":video_game:": "🎮",
    ":dart:": "🎯",
    ":slot_machine:": "🎰",
    ":8ball:": "🎱",
    ":game_die:": "🎲",
    ":bowling:": "🎳",
    ":flower_playing_cards:": "🎴",
    ":musical_note:": "🎵",
    ":notes:": "🎶",
    ":saxophone:": "🎷",
    ":guitar:": "🎸",
    ":musical_keyboard:": "🎹",
    ":trumpet:": "🎺",
    ":violin:": "🎻",
    ":musical_score:": "🎼",
    ":running_shirt_with_sash:": "🎽",
    ":tennis:": "🎾",
    ":ski:": "🎿",
    ":basketball:": "🏀",
    ":checkered_flag:": "🏁",
    ":snowboarder::tone1:": "🏂🏻",
    ":snowboarder::tone2:": "🏂🏼",
    ":snowboarder::tone3:": "🏂🏽",
    ":snowboarder::tone4:": "🏂🏾",
    ":snowboarder::tone5:": "🏂🏿",
    ":snowboarder:": "🏂",
    ":runner_tone1:‍♀️": "🏃🏻‍♀️",
    ":runner_tone1:‍♂️": "🏃🏻‍♂️",
    ":runner_tone1:": "🏃🏻",
    ":runner_tone2:‍♀️": "🏃🏼‍♀️",
    ":runner_tone2:‍♂️": "🏃🏼‍♂️",
    ":runner_tone2:": "🏃🏼",
    ":runner_tone3:‍♀️": "🏃🏽‍♀️",
    ":runner_tone3:‍♂️": "🏃🏽‍♂️",
    ":runner_tone3:": "🏃🏽",
    ":runner_tone4:‍♀️": "🏃🏾‍♀️",
    ":runner_tone4:‍♂️": "🏃🏾‍♂️",
    ":runner_tone4:": "🏃🏾",
    ":runner_tone5:‍♀️": "🏃🏿‍♀️",
    ":runner_tone5:‍♂️": "🏃🏿‍♂️",
    ":runner_tone5:": "🏃🏿",
    ":runner:‍♀️": "🏃‍♀️",
    ":runner:‍♂️": "🏃‍♂️",
    ":runner:": "🏃",
    ":surfer_tone1:‍♀️": "🏄🏻‍♀️",
    ":surfer_tone1:‍♂️": "🏄🏻‍♂️",
    ":surfer_tone1:": "🏄🏻",
    ":surfer_tone2:‍♀️": "🏄🏼‍♀️",
    ":surfer_tone2:‍♂️": "🏄🏼‍♂️",
    ":surfer_tone2:": "🏄🏼",
    ":surfer_tone3:‍♀️": "🏄🏽‍♀️",
    ":surfer_tone3:‍♂️": "🏄🏽‍♂️",
    ":surfer_tone3:": "🏄🏽",
    ":surfer_tone4:‍♀️": "🏄🏾‍♀️",
    ":surfer_tone4:‍♂️": "🏄🏾‍♂️",
    ":surfer_tone4:": "🏄🏾",
    ":surfer_tone5:‍♀️": "🏄🏿‍♀️",
    ":surfer_tone5:‍♂️": "🏄🏿‍♂️",
    ":surfer_tone5:": "🏄🏿",
    ":surfer:‍♀️": "🏄‍♀️",
    ":surfer:‍♂️": "🏄‍♂️",
    ":surfer:": "🏄",
    ":medal:": "🏅",
    ":trophy:": "🏆",
    ":horse_racing_tone1:": "🏇🏻",
    ":horse_racing_tone2:": "🏇🏼",
    ":horse_racing_tone3:": "🏇🏽",
    ":horse_racing_tone4:": "🏇🏾",
    ":horse_racing_tone5:": "🏇🏿",
    ":horse_racing:": "🏇",
    ":football:": "🏈",
    ":rugby_football:": "🏉",
    ":swimmer_tone1:‍♀️": "🏊🏻‍♀️",
    ":swimmer_tone1:‍♂️": "🏊🏻‍♂️",
    ":swimmer_tone1:": "🏊🏻",
    ":swimmer_tone2:‍♀️": "🏊🏼‍♀️",
    ":swimmer_tone2:‍♂️": "🏊🏼‍♂️",
    ":swimmer_tone2:": "🏊🏼",
    ":swimmer_tone3:‍♀️": "🏊🏽‍♀️",
    ":swimmer_tone3:‍♂️": "🏊🏽‍♂️",
    ":swimmer_tone3:": "🏊🏽",
    ":swimmer_tone4:‍♀️": "🏊🏾‍♀️",
    ":swimmer_tone4:‍♂️": "🏊🏾‍♂️",
    ":swimmer_tone4:": "🏊🏾",
    ":swimmer_tone5:‍♀️": "🏊🏿‍♀️",
    ":swimmer_tone5:‍♂️": "🏊🏿‍♂️",
    ":swimmer_tone5:": "🏊🏿",
    ":swimmer:‍♀️": "🏊‍♀️",
    ":swimmer:‍♂️": "🏊‍♂️",
    ":swimmer:": "🏊",
    ":lifter_tone1:‍♀️": "🏋🏻‍♀️",
    ":lifter_tone1:‍♂️": "🏋🏻‍♂️",
    ":lifter_tone1:": "🏋🏻",
    ":lifter_tone2:‍♀️": "🏋🏼‍♀️",
    ":lifter_tone2:‍♂️": "🏋🏼‍♂️",
    ":lifter_tone2:": "🏋🏼",
    ":lifter_tone3:‍♀️": "🏋🏽‍♀️",
    ":lifter_tone3:‍♂️": "🏋🏽‍♂️",
    ":lifter_tone3:": "🏋🏽",
    ":lifter_tone4:‍♀️": "🏋🏾‍♀️",
    ":lifter_tone4:‍♂️": "🏋🏾‍♂️",
    ":lifter_tone4:": "🏋🏾",
    ":lifter_tone5:‍♀️": "🏋🏿‍♀️",
    ":lifter_tone5:‍♂️": "🏋🏿‍♂️",
    ":lifter_tone5:": "🏋🏿",
    ":lifter:‍♀️": "🏋️‍♀️",
    ":lifter:‍♂️": "🏋️‍♂️",
    ":lifter:": "🏋️",
    ":golfer::tone1:‍♀️": "🏌🏻‍♀️",
    ":golfer::tone1:‍♂️": "🏌🏻‍♂️",
    ":golfer::tone1:": "🏌🏻",
    ":golfer::tone2:‍♀️": "🏌🏼‍♀️",
    ":golfer::tone2:‍♂️": "🏌🏼‍♂️",
    ":golfer::tone2:": "🏌🏼",
    ":golfer::tone3:‍♀️": "🏌🏽‍♀️",
    ":golfer::tone3:‍♂️": "🏌🏽‍♂️",
    ":golfer::tone3:": "🏌🏽",
    ":golfer::tone4:‍♀️": "🏌🏾‍♀️",
    ":golfer::tone4:‍♂️": "🏌🏾‍♂️",
    ":golfer::tone4:": "🏌🏾",
    ":golfer::tone5:‍♀️": "🏌🏿‍♀️",
    ":golfer::tone5:‍♂️": "🏌🏿‍♂️",
    ":golfer::tone5:": "🏌🏿",
    ":golfer:‍♀️": "🏌️‍♀️",
    ":golfer:‍♂️": "🏌️‍♂️",
    ":golfer:": "🏌️",
    ":motorcycle:": "🏍️",
    ":race_car:": "🏎️",
    ":cricket:": "🏏",
    ":volleyball:": "🏐",
    ":field_hockey:": "🏑",
    ":hockey:": "🏒",
    ":ping_pong:": "🏓",
    ":mountain_snow:": "🏔️",
    ":camping:": "🏕️",
    ":beach:": "🏖️",
    ":construction_site:": "🏗️",
    ":homes:": "🏘️",
    ":cityscape:": "🏙️",
    ":house_abandoned:": "🏚️",
    ":classical_building:": "🏛️",
    ":desert:": "🏜️",
    ":island:": "🏝️",
    ":park:": "🏞️",
    ":stadium:": "🏟️",
    ":house:": "🏠",
    ":house_with_garden:": "🏡",
    ":office:": "🏢",
    ":post_office:": "🏣",
    ":european_post_office:": "🏤",
    ":hospital:": "🏥",
    ":bank:": "🏦",
    ":atm:": "🏧",
    ":hotel:": "🏨",
    ":love_hotel:": "🏩",
    ":convenience_store:": "🏪",
    ":school:": "🏫",
    ":department_store:": "🏬",
    ":factory:": "🏭",
    ":izakaya_lantern:": "🏮",
    ":japanese_castle:": "🏯",
    ":european_castle:": "🏰",
    ":flag_white:‍:rainbow:": "🏳️‍🌈",
    ":flag_white:": "🏳️",
    ":flag_black:‍:skull_crossbones:": "🏴‍☠️",
    ":flag_black:": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    ":rosette:": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    ":label:": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    ":badminton:": "🏴",
    ":bow_and_arrow:": "🏵️",
    ":amphora:": "🏷️",
    ":tone1:": "🏸",
    ":tone2:": "🏹",
    ":tone3:": "🏺",
    ":tone4:": "🏻",
    ":tone5:": "🏼",
    ":rat:": "🏽",
    ":mouse2:": "🏾",
    ":ox:": "🏿",
    ":water_buffalo:": "🐀",
    ":cow2:": "🐁",
    ":tiger2:": "🐂",
    ":leopard:": "🐃",
    ":rabbit2:": "🐄",
    ":cat2:": "🐅",
    ":dragon:": "🐆",
    ":crocodile:": "🐇",
    ":whale2:": "🐈",
    ":snail:": "🐉",
    ":snake:": "🐊",
    ":racehorse:": "🐋",
    ":ram:": "🐌",
    ":goat:": "🐍",
    ":sheep:": "🐎",
    ":monkey:": "🐏",
    ":rooster:": "🐐",
    ":chicken:": "🐑",
    ":dog2:": "🐒",
    ":pig2:": "🐓",
    ":boar:": "🐔",
    ":elephant:": "🐕‍🦺",
    ":octopus:": "🐕",
    ":shell:": "🐖",
    ":bug:": "🐗",
    ":ant:": "🐘",
    ":bee:": "🐙",
    ":beetle:": "🐚",
    ":fish:": "🐛",
    ":tropical_fish:": "🐜",
    ":blowfish:": "🐝",
    ":turtle:": "🐞",
    ":hatching_chick:": "🐟",
    ":baby_chick:": "🐠",
    ":hatched_chick:": "🐡",
    ":bird:": "🐢",
    ":penguin:": "🐣",
    ":koala:": "🐤",
    ":poodle:": "🐥",
    ":dromedary_camel:": "🐦",
    ":camel:": "🐧",
    ":dolphin:": "🐨",
    ":mouse:": "🐩",
    ":cow:": "🐪",
    ":tiger:": "🐫",
    ":rabbit:": "🐬",
    ":cat:": "🐭",
    ":dragon_face:": "🐮",
    ":whale:": "🐯",
    ":horse:": "🐰",
    ":monkey_face:": "🐱",
    ":dog:": "🐲",
    ":pig:": "🐳",
    ":frog:": "🐴",
    ":hamster:": "🐵",
    ":wolf:": "🐶",
    ":bear:": "🐷",
    ":panda_face:": "🐸",
    ":pig_nose:": "🐹",
    ":feet:": "🐺",
    ":chipmunk:": "🐻",
    ":eyes:": "🐼",
    ":eye_in_speech_bubble:": "🐽",
    ":eye:": "🐾",
    ":ear_tone1:": "🐿️",
    ":ear_tone2:": "👀",
    ":ear_tone3:": "👁‍🗨",
    ":ear_tone4:": "👁️",
    ":ear_tone5:": "👂🏻",
    ":ear:": "👂🏼",
    ":nose_tone1:": "👂🏽",
    ":nose_tone2:": "👂🏾",
    ":nose_tone3:": "👂🏿",
    ":nose_tone4:": "👂",
    ":nose_tone5:": "👃🏻",
    ":nose:": "👃🏼",
    ":lips:": "👃🏽",
    ":tongue:": "👃🏾",
    ":point_up_2_tone1:": "👃🏿",
    ":point_up_2_tone2:": "👃",
    ":point_up_2_tone3:": "👄",
    ":point_up_2_tone4:": "👅",
    ":point_up_2_tone5:": "👆🏻",
    ":point_up_2:": "👆🏼",
    ":point_down_tone1:": "👆🏽",
    ":point_down_tone2:": "👆🏾",
    ":point_down_tone3:": "👆🏿",
    ":point_down_tone4:": "👆",
    ":point_down_tone5:": "👇🏻",
    ":point_down:": "👇🏼",
    ":point_left_tone1:": "👇🏽",
    ":point_left_tone2:": "👇🏾",
    ":point_left_tone3:": "👇🏿",
    ":point_left_tone4:": "👇",
    ":point_left_tone5:": "👈🏻",
    ":point_left:": "👈🏼",
    ":point_right_tone1:": "👈🏽",
    ":point_right_tone2:": "👈🏾",
    ":point_right_tone3:": "👈🏿",
    ":point_right_tone4:": "👈",
    ":point_right_tone5:": "👉🏻",
    ":point_right:": "👉🏼",
    ":punch_tone1:": "👉🏽",
    ":punch_tone2:": "👉🏾",
    ":punch_tone3:": "👉🏿",
    ":punch_tone4:": "👉",
    ":punch_tone5:": "👊🏻",
    ":punch:": "👊🏼",
    ":wave_tone1:": "👊🏽",
    ":wave_tone2:": "👊🏾",
    ":wave_tone3:": "👊🏿",
    ":wave_tone4:": "👊",
    ":wave_tone5:": "👋🏻",
    ":wave:": "👋🏼",
    ":ok_hand_tone1:": "👋🏽",
    ":ok_hand_tone2:": "👋🏾",
    ":ok_hand_tone3:": "👋🏿",
    ":ok_hand_tone4:": "👋",
    ":ok_hand_tone5:": "👌🏻",
    ":ok_hand:": "👌🏼",
    ":thumbsup_tone1:": "👌🏽",
    ":thumbsup_tone2:": "👌🏾",
    ":thumbsup_tone3:": "👌🏿",
    ":thumbsup_tone4:": "👌",
    ":thumbsup_tone5:": "👍🏻",
    ":thumbsup:": "👍🏼",
    ":thumbsdown_tone1:": "👍🏽",
    ":thumbsdown_tone2:": "👍🏾",
    ":thumbsdown_tone3:": "👍🏿",
    ":thumbsdown_tone4:": "👍",
    ":thumbsdown_tone5:": "👎🏻",
    ":thumbsdown:": "👎🏼",
    ":clap_tone1:": "👎🏽",
    ":clap_tone2:": "👎🏾",
    ":clap_tone3:": "👎🏿",
    ":clap_tone4:": "👎",
    ":clap_tone5:": "👏🏻",
    ":clap:": "👏🏼",
    ":open_hands_tone1:": "👏🏽",
    ":open_hands_tone2:": "👏🏾",
    ":open_hands_tone3:": "👏🏿",
    ":open_hands_tone4:": "👏",
    ":open_hands_tone5:": "👐🏻",
    ":open_hands:": "👐🏼",
    ":crown:": "👐🏽",
    ":womans_hat:": "👐🏾",
    ":eyeglasses:": "👐🏿",
    ":necktie:": "👐",
    ":shirt:": "👑",
    ":jeans:": "👒",
    ":dress:": "👓",
    ":kimono:": "👔",
    ":bikini:": "👕",
    ":womans_clothes:": "👖",
    ":purse:": "👗",
    ":handbag:": "👘",
    ":pouch:": "👙",
    ":mans_shoe:": "👚",
    ":athletic_shoe:": "👛",
    ":high_heel:": "👜",
    ":sandal:": "👝",
    ":boot:": "👞",
    ":footprints:": "👟",
    ":bust_in_silhouette:": "👠",
    ":busts_in_silhouette:": "👡",
    ":boy_tone1:": "👢",
    ":boy_tone2:": "👣",
    ":boy_tone3:": "👤",
    ":boy_tone4:": "👥",
    ":boy_tone5:": "👦🏻",
    ":boy:": "👦🏼",
    ":girl_tone1:": "👦🏽",
    ":girl_tone2:": "👦🏾",
    ":girl_tone3:": "👦🏿",
    ":girl_tone4:": "👦",
    ":girl_tone5:": "👧🏻",
    ":girl:": "👧🏼",
    ":man_tone1:‍:ear_of_rice:": "👧🏽",
    ":man_tone1:‍:cooking:": "👧🏾",
    ":man_tone1:‍:mortar_board:": "👧🏿",
    ":man_tone1:‍:microphone:": "👧",
    ":man_tone1:‍:art:": "👨🏻‍🌾",
    ":man_tone1:‍:school:": "👨🏻‍🍳",
    ":man_tone1:‍:factory:": "👨🏻‍🎓",
    ":man_tone1:‍:computer:": "👨🏻‍🎤",
    ":man_tone1:‍:briefcase:": "👨🏻‍🎨",
    ":man_tone1:‍:wrench:": "👨🏻‍🏫",
    ":man_tone1:‍:microscope:": "👨🏻‍🏭",
    ":man_tone1:‍:rocket:": "👨🏻‍💻",
    ":man_tone1:‍:fire_engine:": "👨🏻‍💼",
    ":man_tone1:‍⚕️": "👨🏻‍🔧",
    ":man_tone1:‍:scales:": "👨🏻‍🔬",
    ":man_tone1:‍:airplane:": "👨🏻‍🚀",
    ":man_tone1:": "👨🏻‍🚒",
    ":man_tone2:‍:ear_of_rice:": "👨🏻‍🦯",
    ":man_tone2:‍:cooking:": "👨🏻‍🦰",
    ":man_tone2:‍:mortar_board:": "👨🏻‍🦱",
    ":man_tone2:‍:microphone:": "👨🏻‍🦲",
    ":man_tone2:‍:art:": "👨🏻‍🦳",
    ":man_tone2:‍:school:": "👨🏻‍🦼",
    ":man_tone2:‍:factory:": "👨🏻‍🦽",
    ":man_tone2:‍:computer:": "👨🏻‍⚕️",
    ":man_tone2:‍:briefcase:": "👨🏻‍⚖️",
    ":man_tone2:‍:wrench:": "👨🏻‍✈️",
    ":man_tone2:‍:microscope:": "👨🏻",
    ":man_tone2:‍:rocket:": "👨🏼‍🌾",
    ":man_tone2:‍:fire_engine:": "👨🏼‍🍳",
    ":man_tone2:‍⚕️": "👨🏼‍🎓",
    ":man_tone2:‍:scales:": "👨🏼‍🎤",
    ":man_tone2:‍:airplane:": "👨🏼‍🎨",
    ":man_tone2:": "👨🏼‍🏫",
    ":man_tone3:‍:ear_of_rice:": "👨🏼‍🏭",
    ":man_tone3:‍:cooking:": "👨🏼‍💻",
    ":man_tone3:‍:mortar_board:": "👨🏼‍💼",
    ":man_tone3:‍:microphone:": "👨🏼‍🔧",
    ":man_tone3:‍:art:": "👨🏼‍🔬",
    ":man_tone3:‍:school:": "👨🏼‍🚀",
    ":man_tone3:‍:factory:": "👨🏼‍🚒",
    ":man_tone3:‍:computer:": "👨🏼‍🤝‍👨🏻",
    ":man_tone3:‍:briefcase:": "👨🏼‍🦯",
    ":man_tone3:‍:wrench:": "👨🏼‍🦰",
    ":man_tone3:‍:microscope:": "👨🏼‍🦱",
    ":man_tone3:‍:rocket:": "👨🏼‍🦲",
    ":man_tone3:‍:fire_engine:": "👨🏼‍🦳",
    ":man_tone3:‍⚕️": "👨🏼‍🦼",
    ":man_tone3:‍:scales:": "👨🏼‍🦽",
    ":man_tone3:‍:airplane:": "👨🏼‍⚕️",
    ":man_tone3:": "👨🏼‍⚖️",
    ":man_tone4:‍:ear_of_rice:": "👨🏼‍✈️",
    ":man_tone4:‍:cooking:": "👨🏼",
    ":man_tone4:‍:mortar_board:": "👨🏽‍🌾",
    ":man_tone4:‍:microphone:": "👨🏽‍🍳",
    ":man_tone4:‍:art:": "👨🏽‍🎓",
    ":man_tone4:‍:school:": "👨🏽‍🎤",
    ":man_tone4:‍:factory:": "👨🏽‍🎨",
    ":man_tone4:‍:computer:": "👨🏽‍🏫",
    ":man_tone4:‍:briefcase:": "👨🏽‍🏭",
    ":man_tone4:‍:wrench:": "👨🏽‍💻",
    ":man_tone4:‍:microscope:": "👨🏽‍💼",
    ":man_tone4:‍:rocket:": "👨🏽‍🔧",
    ":man_tone4:‍:fire_engine:": "👨🏽‍🔬",
    ":man_tone4:‍⚕️": "👨🏽‍🚀",
    ":man_tone4:‍:scales:": "👨🏽‍🚒",
    ":man_tone4:‍:airplane:": "👨🏽‍🤝‍👨🏻",
    ":man_tone4:": "👨🏽‍🤝‍👨🏼",
    ":man_tone5:‍:ear_of_rice:": "👨🏽‍🦯",
    ":man_tone5:‍:cooking:": "👨🏽‍🦰",
    ":man_tone5:‍:mortar_board:": "👨🏽‍🦱",
    ":man_tone5:‍:microphone:": "👨🏽‍🦲",
    ":man_tone5:‍:art:": "👨🏽‍🦳",
    ":man_tone5:‍:school:": "👨🏽‍🦼",
    ":man_tone5:‍:factory:": "👨🏽‍🦽",
    ":man_tone5:‍:computer:": "👨🏽‍⚕️",
    ":man_tone5:‍:briefcase:": "👨🏽‍⚖️",
    ":man_tone5:‍:wrench:": "👨🏽‍✈️",
    ":man_tone5:‍:microscope:": "👨🏽",
    ":man_tone5:‍:rocket:": "👨🏾‍🌾",
    ":man_tone5:‍:fire_engine:": "👨🏾‍🍳",
    ":man_tone5:‍⚕️": "👨🏾‍🎓",
    ":man_tone5:‍:scales:": "👨🏾‍🎤",
    ":man_tone5:‍:airplane:": "👨🏾‍🎨",
    ":man_tone5:": "👨🏾‍🏫",
    ":man:‍:ear_of_rice:": "👨🏾‍🏭",
    ":man:‍:cooking:": "👨🏾‍💻",
    ":man:‍:mortar_board:": "👨🏾‍💼",
    ":man:‍:microphone:": "👨🏾‍🔧",
    ":man:‍:art:": "👨🏾‍🔬",
    ":man:‍:school:": "👨🏾‍🚀",
    ":man:‍:factory:": "👨🏾‍🚒",
    ":man:‍:boy:‍:boy:": "👨🏾‍🤝‍👨🏻",
    ":man:‍:boy:": "👨🏾‍🤝‍👨🏼",
    ":man:‍:girl:‍:boy:": "👨🏾‍🤝‍👨🏽",
    ":man:‍:girl:‍:girl:": "👨🏾‍🦯",
    ":man:‍:girl:": "👨🏾‍🦰",
    ":family_mmbb:": "👨🏾‍🦱",
    ":family_mmb:": "👨🏾‍🦲",
    ":family_mmgb:": "👨🏾‍🦳",
    ":family_mmgg:": "👨🏾‍🦼",
    ":family_mmg:": "👨🏾‍🦽",
    ":family_mwbb:": "👨🏾‍⚕️",
    ":man:‍:woman:‍:boy:": "👨🏾‍⚖️",
    ":family_mwgb:": "👨🏾‍✈️",
    ":family_mwgg:": "👨🏾",
    ":family_mwg:": "👨🏿‍🌾",
    ":man:‍:computer:": "👨🏿‍🍳",
    ":man:‍:briefcase:": "👨🏿‍🎓",
    ":man:‍:wrench:": "👨🏿‍🎤",
    ":man:‍:microscope:": "👨🏿‍🎨",
    ":man:‍:rocket:": "👨🏿‍🏫",
    ":man:‍:fire_engine:": "👨🏿‍🏭",
    ":man:‍⚕️": "👨🏿‍💻",
    ":man:‍:scales:": "👨🏿‍💼",
    ":man:‍:airplane:": "👨🏿‍🔧",
    ":couple_mm:": "👨🏿‍🔬",
    ":kiss_mm:": "👨🏿‍🚀",
    ":man:": "👨🏿‍🚒",
    ":woman_tone1:‍:ear_of_rice:": "👨🏿‍🤝‍👨🏻",
    ":woman_tone1:‍:cooking:": "👨🏿‍🤝‍👨🏼",
    ":woman_tone1:‍:mortar_board:": "👨🏿‍🤝‍👨🏽",
    ":woman_tone1:‍:microphone:": "👨🏿‍🤝‍👨🏾",
    ":woman_tone1:‍:art:": "👨🏿‍🦯",
    ":woman_tone1:‍:school:": "👨🏿‍🦰",
    ":woman_tone1:‍:factory:": "👨🏿‍🦱",
    ":woman_tone1:‍:computer:": "👨🏿‍🦲",
    ":woman_tone1:‍:briefcase:": "👨🏿‍🦳",
    ":woman_tone1:‍:wrench:": "👨🏿‍🦼",
    ":woman_tone1:‍:microscope:": "👨🏿‍🦽",
    ":woman_tone1:‍:rocket:": "👨🏿‍⚕️",
    ":woman_tone1:‍:fire_engine:": "👨🏿‍⚖️",
    ":woman_tone1:‍⚕️": "👨🏿‍✈️",
    ":woman_tone1:‍:scales:": "👨🏿",
    ":woman_tone1:‍:airplane:": "👨‍🌾",
    ":woman_tone1:": "👨‍🍳",
    ":woman_tone2:‍:ear_of_rice:": "👨‍🎓",
    ":woman_tone2:‍:cooking:": "👨‍🎤",
    ":woman_tone2:‍:mortar_board:": "👨‍🎨",
    ":woman_tone2:‍:microphone:": "👨‍🏫",
    ":woman_tone2:‍:art:": "👨‍🏭",
    ":woman_tone2:‍:school:": "👨‍👦‍👦",
    ":woman_tone2:‍:factory:": "👨‍👦",
    ":woman_tone2:‍:computer:": "👨‍👧‍👦",
    ":woman_tone2:‍:briefcase:": "👨‍👧‍👧",
    ":woman_tone2:‍:wrench:": "👨‍👧",
    ":woman_tone2:‍:microscope:": "👨‍👨‍👦‍👦",
    ":woman_tone2:‍:rocket:": "👨‍👨‍👦",
    ":woman_tone2:‍:fire_engine:": "👨‍👨‍👧‍👦",
    ":woman_tone2:‍⚕️": "👨‍👨‍👧‍👧",
    ":woman_tone2:‍:scales:": "👨‍👨‍👧",
    ":woman_tone2:‍:airplane:": "👨‍👩‍👦‍👦",
    ":woman_tone2:": "👨‍👩‍👦",
    ":woman_tone3:‍:ear_of_rice:": "👨‍👩‍👧‍👦",
    ":woman_tone3:‍:cooking:": "👨‍👩‍👧‍👧",
    ":woman_tone3:‍:mortar_board:": "👨‍👩‍👧",
    ":woman_tone3:‍:microphone:": "👨‍💻",
    ":woman_tone3:‍:art:": "👨‍💼",
    ":woman_tone3:‍:school:": "👨‍🔧",
    ":woman_tone3:‍:factory:": "👨‍🔬",
    ":woman_tone3:‍:computer:": "👨‍🚀",
    ":woman_tone3:‍:briefcase:": "👨‍🚒",
    ":woman_tone3:‍:wrench:": "👨‍🦯",
    ":woman_tone3:‍:microscope:": "👨‍🦰",
    ":woman_tone3:‍:rocket:": "👨‍🦱",
    ":woman_tone3:‍:fire_engine:": "👨‍🦲",
    ":woman_tone3:‍⚕️": "👨‍🦳",
    ":woman_tone3:‍:scales:": "👨‍🦼",
    ":woman_tone3:‍:airplane:": "👨‍🦽",
    ":woman_tone3:": "👨‍⚕️",
    ":woman_tone4:‍:ear_of_rice:": "👨‍⚖️",
    ":woman_tone4:‍:cooking:": "👨‍✈️",
    ":woman_tone4:‍:mortar_board:": "👨‍❤️‍👨",
    ":woman_tone4:‍:microphone:": "👨‍❤️‍💋‍👨",
    ":woman_tone4:‍:art:": "👨",
    ":woman_tone4:‍:school:": "👩🏻‍🌾",
    ":woman_tone4:‍:factory:": "👩🏻‍🍳",
    ":woman_tone4:‍:computer:": "👩🏻‍🎓",
    ":woman_tone4:‍:briefcase:": "👩🏻‍🎤",
    ":woman_tone4:‍:wrench:": "👩🏻‍🎨",
    ":woman_tone4:‍:microscope:": "👩🏻‍🏫",
    ":woman_tone4:‍:rocket:": "👩🏻‍🏭",
    ":woman_tone4:‍:fire_engine:": "👩🏻‍💻",
    ":woman_tone4:‍⚕️": "👩🏻‍💼",
    ":woman_tone4:‍:scales:": "👩🏻‍🔧",
    ":woman_tone4:‍:airplane:": "👩🏻‍🔬",
    ":woman_tone4:": "👩🏻‍🚀",
    ":woman_tone5:‍:ear_of_rice:": "👩🏻‍🚒",
    ":woman_tone5:‍:cooking:": "👩🏻‍🤝‍👨🏼",
    ":woman_tone5:‍:mortar_board:": "👩🏻‍🤝‍👨🏽",
    ":woman_tone5:‍:microphone:": "👩🏻‍🤝‍👨🏾",
    ":woman_tone5:‍:art:": "👩🏻‍🤝‍👨🏿",
    ":woman_tone5:‍:school:": "👩🏻‍🦯",
    ":woman_tone5:‍:factory:": "👩🏻‍🦰",
    ":woman_tone5:‍:computer:": "👩🏻‍🦱",
    ":woman_tone5:‍:briefcase:": "👩🏻‍🦲",
    ":woman_tone5:‍:wrench:": "👩🏻‍🦳",
    ":woman_tone5:‍:microscope:": "👩🏻‍🦼",
    ":woman_tone5:‍:rocket:": "👩🏻‍🦽",
    ":woman_tone5:‍:fire_engine:": "👩🏻‍⚕️",
    ":woman_tone5:‍⚕️": "👩🏻‍⚖️",
    ":woman_tone5:‍:scales:": "👩🏻‍✈️",
    ":woman_tone5:‍:airplane:": "👩🏻",
    ":woman_tone5:": "👩🏼‍🌾",
    ":woman:‍:ear_of_rice:": "👩🏼‍🍳",
    ":woman:‍:cooking:": "👩🏼‍🎓",
    ":woman:‍:mortar_board:": "👩🏼‍🎤",
    ":woman:‍:microphone:": "👩🏼‍🎨",
    ":woman:‍:art:": "👩🏼‍🏫",
    ":woman:‍:school:": "👩🏼‍🏭",
    ":woman:‍:factory:": "👩🏼‍💻",
    ":woman:‍:boy:‍:boy:": "👩🏼‍💼",
    ":woman:‍:boy:": "👩🏼‍🔧",
    ":woman:‍:girl:‍:boy:": "👩🏼‍🔬",
    ":woman:‍:girl:‍:girl:": "👩🏼‍🚀",
    ":woman:‍:girl:": "👩🏼‍🚒",
    ":family_wwbb:": "👩🏼‍🤝‍👨🏻",
    ":family_wwb:": "👩🏼‍🤝‍👨🏽",
    ":family_wwgb:": "👩🏼‍🤝‍👨🏾",
    ":family_wwgg:": "👩🏼‍🤝‍👨🏿",
    ":family_wwg:": "👩🏼‍🤝‍👩🏻",
    ":woman:‍:computer:": "👩🏼‍🦯",
    ":woman:‍:briefcase:": "👩🏼‍🦰",
    ":woman:‍:wrench:": "👩🏼‍🦱",
    ":woman:‍:microscope:": "👩🏼‍🦲",
    ":woman:‍:rocket:": "👩🏼‍🦳",
    ":woman:‍:fire_engine:": "👩🏼‍🦼",
    ":woman:‍⚕️": "👩🏼‍🦽",
    ":woman:‍:scales:": "👩🏼‍⚕️",
    ":woman:‍:airplane:": "👩🏼‍⚖️",
    ":woman:‍:heart:‍:man:": "👩🏼‍✈️",
    ":couple_ww:": "👩🏼",
    ":woman:‍:heart:‍:kiss:‍:man:": "👩🏽‍🌾",
    ":kiss_ww:": "👩🏽‍🍳",
    ":woman:": "👩🏽‍🎓",
    ":family::tone1:": "👩🏽‍🎤",
    ":family::tone2:": "👩🏽‍🎨",
    ":family::tone3:": "👩🏽‍🏫",
    ":family::tone4:": "👩🏽‍🏭",
    ":family::tone5:": "👩🏽‍💻",
    ":family:": "👩🏽‍💼",
    ":couple::tone1:": "👩🏽‍🔧",
    ":couple::tone2:": "👩🏽‍🔬",
    ":couple::tone3:": "👩🏽‍🚀",
    ":couple::tone4:": "👩🏽‍🚒",
    ":couple::tone5:": "👩🏽‍🤝‍👨🏻",
    ":couple:": "👩🏽‍🤝‍👨🏼",
    ":two_men_holding_hands::tone1:": "👩🏽‍🤝‍👨🏾",
    ":two_men_holding_hands::tone2:": "👩🏽‍🤝‍👨🏿",
    ":two_men_holding_hands::tone3:": "👩🏽‍🤝‍👩🏻",
    ":two_men_holding_hands::tone4:": "👩🏽‍🤝‍👩🏼",
    ":two_men_holding_hands::tone5:": "👩🏽‍🦯",
    ":two_men_holding_hands:": "👩🏽‍🦰",
    ":two_women_holding_hands::tone1:": "👩🏽‍🦱",
    ":two_women_holding_hands::tone2:": "👩🏽‍🦲",
    ":two_women_holding_hands::tone3:": "👩🏽‍🦳",
    ":two_women_holding_hands::tone4:": "👩🏽‍🦼",
    ":two_women_holding_hands::tone5:": "👩🏽‍🦽",
    ":two_women_holding_hands:": "👩🏽‍⚕️",
    ":cop_tone1:‍♀️": "👩🏽‍⚖️",
    ":cop_tone1:‍♂️": "👩🏽‍✈️",
    ":cop_tone1:": "👩🏽",
    ":cop_tone2:‍♀️": "👩🏾‍🌾",
    ":cop_tone2:‍♂️": "👩🏾‍🍳",
    ":cop_tone2:": "👩🏾‍🎓",
    ":cop_tone3:‍♀️": "👩🏾‍🎤",
    ":cop_tone3:‍♂️": "👩🏾‍🎨",
    ":cop_tone3:": "👩🏾‍🏫",
    ":cop_tone4:‍♀️": "👩🏾‍🏭",
    ":cop_tone4:‍♂️": "👩🏾‍💻",
    ":cop_tone4:": "👩🏾‍💼",
    ":cop_tone5:‍♀️": "👩🏾‍🔧",
    ":cop_tone5:‍♂️": "👩🏾‍🔬",
    ":cop_tone5:": "👩🏾‍🚀",
    ":cop:‍♀️": "👩🏾‍🚒",
    ":cop:‍♂️": "👩🏾‍🤝‍👨🏻",
    ":cop:": "👩🏾‍🤝‍👨🏼",
    ":dancers::tone1:‍♀️": "👩🏾‍🤝‍👨🏽",
    ":dancers::tone1:‍♂️": "👩🏾‍🤝‍👨🏿",
    ":dancers::tone1:": "👩🏾‍🤝‍👩🏻",
    ":dancers::tone2:‍♀️": "👩🏾‍🤝‍👩🏼",
    ":dancers::tone2:‍♂️": "👩🏾‍🤝‍👩🏽",
    ":dancers::tone2:": "👩🏾‍🦯",
    ":dancers::tone3:‍♀️": "👩🏾‍🦰",
    ":dancers::tone3:‍♂️": "👩🏾‍🦱",
    ":dancers::tone3:": "👩🏾‍🦲",
    ":dancers::tone4:‍♀️": "👩🏾‍🦳",
    ":dancers::tone4:‍♂️": "👩🏾‍🦼",
    ":dancers::tone4:": "👩🏾‍🦽",
    ":dancers::tone5:‍♀️": "👩🏾‍⚕️",
    ":dancers::tone5:‍♂️": "👩🏾‍⚖️",
    ":dancers::tone5:": "👩🏾‍✈️",
    ":dancers:‍♀️": "👩🏾",
    ":dancers:‍♂️": "👩🏿‍🌾",
    ":dancers:": "👩🏿‍🍳",
    ":bride_with_veil_tone1:": "👩🏿‍🎓",
    ":bride_with_veil_tone2:": "👩🏿‍🎤",
    ":bride_with_veil_tone3:": "👩🏿‍🎨",
    ":bride_with_veil_tone4:": "👩🏿‍🏫",
    ":bride_with_veil_tone5:": "👩🏿‍🏭",
    ":bride_with_veil:": "👩🏿‍💻",
    ":person_with_blond_hair_tone1:‍♀️": "👩🏿‍💼",
    ":person_with_blond_hair_tone1:‍♂️": "👩🏿‍🔧",
    ":person_with_blond_hair_tone1:": "👩🏿‍🔬",
    ":person_with_blond_hair_tone2:‍♀️": "👩🏿‍🚀",
    ":person_with_blond_hair_tone2:‍♂️": "👩🏿‍🚒",
    ":person_with_blond_hair_tone2:": "👩🏿‍🤝‍👨🏻",
    ":person_with_blond_hair_tone3:‍♀️": "👩🏿‍🤝‍👨🏼",
    ":person_with_blond_hair_tone3:‍♂️": "👩🏿‍🤝‍👨🏽",
    ":person_with_blond_hair_tone3:": "👩🏿‍🤝‍👨🏾",
    ":person_with_blond_hair_tone4:‍♀️": "👩🏿‍🤝‍👩🏻",
    ":person_with_blond_hair_tone4:‍♂️": "👩🏿‍🤝‍👩🏼",
    ":person_with_blond_hair_tone4:": "👩🏿‍🤝‍👩🏽",
    ":person_with_blond_hair_tone5:‍♀️": "👩🏿‍🤝‍👩🏾",
    ":person_with_blond_hair_tone5:‍♂️": "👩🏿‍🦯",
    ":person_with_blond_hair_tone5:": "👩🏿‍🦰",
    ":person_with_blond_hair:‍♀️": "👩🏿‍🦱",
    ":person_with_blond_hair:‍♂️": "👩🏿‍🦲",
    ":person_with_blond_hair:": "👩🏿‍🦳",
    ":man_with_gua_pi_mao_tone1:": "👩🏿‍🦼",
    ":man_with_gua_pi_mao_tone2:": "👩🏿‍🦽",
    ":man_with_gua_pi_mao_tone3:": "👩🏿‍⚕️",
    ":man_with_gua_pi_mao_tone4:": "👩🏿‍⚖️",
    ":man_with_gua_pi_mao_tone5:": "👩🏿‍✈️",
    ":man_with_gua_pi_mao:": "👩🏿",
    ":man_with_turban_tone1:‍♀️": "👩‍🌾",
    ":man_with_turban_tone1:‍♂️": "👩‍🍳",
    ":man_with_turban_tone1:": "👩‍🎓",
    ":man_with_turban_tone2:‍♀️": "👩‍🎤",
    ":man_with_turban_tone2:‍♂️": "👩‍🎨",
    ":man_with_turban_tone2:": "👩‍🏫",
    ":man_with_turban_tone3:‍♀️": "👩‍🏭",
    ":man_with_turban_tone3:‍♂️": "👩‍👦‍👦",
    ":man_with_turban_tone3:": "👩‍👦",
    ":man_with_turban_tone4:‍♀️": "👩‍👧‍👦",
    ":man_with_turban_tone4:‍♂️": "👩‍👧‍👧",
    ":man_with_turban_tone4:": "👩‍👧",
    ":man_with_turban_tone5:‍♀️": "👩‍👩‍👦‍👦",
    ":man_with_turban_tone5:‍♂️": "👩‍👩‍👦",
    ":man_with_turban_tone5:": "👩‍👩‍👧‍👦",
    ":man_with_turban:‍♀️": "👩‍👩‍👧‍👧",
    ":man_with_turban:‍♂️": "👩‍👩‍👧",
    ":man_with_turban:": "👩‍💻",
    ":older_man_tone1:": "👩‍💼",
    ":older_man_tone2:": "👩‍🔧",
    ":older_man_tone3:": "👩‍🔬",
    ":older_man_tone4:": "👩‍🚀",
    ":older_man_tone5:": "👩‍🚒",
    ":older_man:": "👩‍🦯",
    ":older_woman_tone1:": "👩‍🦰",
    ":older_woman_tone2:": "👩‍🦱",
    ":older_woman_tone3:": "👩‍🦲",
    ":older_woman_tone4:": "👩‍🦳",
    ":older_woman_tone5:": "👩‍🦼",
    ":older_woman:": "👩‍🦽",
    ":baby_tone1:": "👩‍⚕️",
    ":baby_tone2:": "👩‍⚖️",
    ":baby_tone3:": "👩‍✈️",
    ":baby_tone4:": "👩‍❤️‍👨",
    ":baby_tone5:": "👩‍❤️‍👩",
    ":baby:": "👩‍❤️‍💋‍👨",
    ":construction_worker_tone1:‍♀️": "👩‍❤️‍💋‍👩",
    ":construction_worker_tone1:‍♂️": "👩",
    ":construction_worker_tone1:": "👪",
    ":construction_worker_tone2:‍♀️": "👫🏻",
    ":construction_worker_tone2:‍♂️": "👫🏼",
    ":construction_worker_tone2:": "👫🏽",
    ":construction_worker_tone3:‍♀️": "👫🏾",
    ":construction_worker_tone3:‍♂️": "👫🏿",
    ":construction_worker_tone3:": "👫",
    ":construction_worker_tone4:‍♀️": "👬🏻",
    ":construction_worker_tone4:‍♂️": "👬🏼",
    ":construction_worker_tone4:": "👬🏽",
    ":construction_worker_tone5:‍♀️": "👬🏾",
    ":construction_worker_tone5:‍♂️": "👬🏿",
    ":construction_worker_tone5:": "👬",
    ":construction_worker:‍♀️": "👭🏻",
    ":construction_worker:‍♂️": "👭🏼",
    ":construction_worker:": "👭🏽",
    ":princess_tone1:": "👭🏾",
    ":princess_tone2:": "👭🏿",
    ":princess_tone3:": "👭",
    ":princess_tone4:": "👮🏻‍♀️",
    ":princess_tone5:": "👮🏻‍♂️",
    ":princess:": "👮🏻",
    ":japanese_ogre:": "👮🏼‍♀️",
    ":japanese_goblin:": "👮🏼‍♂️",
    ":ghost:": "👮🏼",
    ":angel_tone1:": "👮🏽‍♀️",
    ":angel_tone2:": "👮🏽‍♂️",
    ":angel_tone3:": "👮🏽",
    ":angel_tone4:": "👮🏾‍♀️",
    ":angel_tone5:": "👮🏾‍♂️",
    ":angel:": "👮🏾",
    ":alien:": "👮🏿‍♀️",
    ":space_invader:": "👮🏿‍♂️",
    ":imp:": "👮🏿",
    ":skull:": "👮‍♀️",
    ":information_desk_person_tone1:‍♀️": "👮‍♂️",
    ":information_desk_person_tone1:‍♂️": "👮",
    ":information_desk_person_tone1:": "👯‍♀️",
    ":information_desk_person_tone2:‍♀️": "👯‍♂️",
    ":information_desk_person_tone2:‍♂️": "👯",
    ":information_desk_person_tone2:": "👰🏻",
    ":information_desk_person_tone3:‍♀️": "👰🏼",
    ":information_desk_person_tone3:‍♂️": "👰🏽",
    ":information_desk_person_tone3:": "👰🏾",
    ":information_desk_person_tone4:‍♀️": "👰🏿",
    ":information_desk_person_tone4:‍♂️": "👰",
    ":information_desk_person_tone4:": "👱🏻‍♀️",
    ":information_desk_person_tone5:‍♀️": "👱🏻‍♂️",
    ":information_desk_person_tone5:‍♂️": "👱🏻",
    ":information_desk_person_tone5:": "👱🏼‍♀️",
    ":information_desk_person:‍♀️": "👱🏼‍♂️",
    ":information_desk_person:‍♂️": "👱🏼",
    ":information_desk_person:": "👱🏽‍♀️",
    ":guardsman_tone1:‍♀️": "👱🏽‍♂️",
    ":guardsman_tone1:‍♂️": "👱🏽",
    ":guardsman_tone1:": "👱🏾‍♀️",
    ":guardsman_tone2:‍♀️": "👱🏾‍♂️",
    ":guardsman_tone2:‍♂️": "👱🏾",
    ":guardsman_tone2:": "👱🏿‍♀️",
    ":guardsman_tone3:‍♀️": "👱🏿‍♂️",
    ":guardsman_tone3:‍♂️": "👱🏿",
    ":guardsman_tone3:": "👱‍♀️",
    ":guardsman_tone4:‍♀️": "👱‍♂️",
    ":guardsman_tone4:‍♂️": "👱",
    ":guardsman_tone4:": "👲🏻",
    ":guardsman_tone5:‍♀️": "👲🏼",
    ":guardsman_tone5:‍♂️": "👲🏽",
    ":guardsman_tone5:": "👲🏾",
    ":guardsman:‍♀️": "👲🏿",
    ":guardsman:‍♂️": "👲",
    ":guardsman:": "👳🏻‍♀️",
    ":dancer_tone1:": "👳🏻‍♂️",
    ":dancer_tone2:": "👳🏻",
    ":dancer_tone3:": "👳🏼‍♀️",
    ":dancer_tone4:": "👳🏼‍♂️",
    ":dancer_tone5:": "👳🏼",
    ":dancer:": "👳🏽‍♀️",
    ":lipstick:": "👳🏽‍♂️",
    ":nail_care_tone1:": "👳🏽",
    ":nail_care_tone2:": "👳🏾‍♀️",
    ":nail_care_tone3:": "👳🏾‍♂️",
    ":nail_care_tone4:": "👳🏾",
    ":nail_care_tone5:": "👳🏿‍♀️",
    ":nail_care:": "👳🏿‍♂️",
    ":massage_tone1:‍♀️": "👳🏿",
    ":massage_tone1:‍♂️": "👳‍♀️",
    ":massage_tone1:": "👳‍♂️",
    ":massage_tone2:‍♀️": "👳",
    ":massage_tone2:‍♂️": "👴🏻",
    ":massage_tone2:": "👴🏼",
    ":massage_tone3:‍♀️": "👴🏽",
    ":massage_tone3:‍♂️": "👴🏾",
    ":massage_tone3:": "👴🏿",
    ":massage_tone4:‍♀️": "👴",
    ":massage_tone4:‍♂️": "👵🏻",
    ":massage_tone4:": "👵🏼",
    ":massage_tone5:‍♀️": "👵🏽",
    ":massage_tone5:‍♂️": "👵🏾",
    ":massage_tone5:": "👵🏿",
    ":massage:‍♀️": "👵",
    ":massage:‍♂️": "👶🏻",
    ":massage:": "👶🏼",
    ":haircut_tone1:‍♀️": "👶🏽",
    ":haircut_tone1:‍♂️": "👶🏾",
    ":haircut_tone1:": "👶🏿",
    ":haircut_tone2:‍♀️": "👶",
    ":haircut_tone2:‍♂️": "👷🏻‍♀️",
    ":haircut_tone2:": "👷🏻‍♂️",
    ":haircut_tone3:‍♀️": "👷🏻",
    ":haircut_tone3:‍♂️": "👷🏼‍♀️",
    ":haircut_tone3:": "👷🏼‍♂️",
    ":haircut_tone4:‍♀️": "👷🏼",
    ":haircut_tone4:‍♂️": "👷🏽‍♀️",
    ":haircut_tone4:": "👷🏽‍♂️",
    ":haircut_tone5:‍♀️": "👷🏽",
    ":haircut_tone5:‍♂️": "👷🏾‍♀️",
    ":haircut_tone5:": "👷🏾‍♂️",
    ":haircut:‍♀️": "👷🏾",
    ":haircut:‍♂️": "👷🏿‍♀️",
    ":haircut:": "👷🏿‍♂️",
    ":barber:": "👷🏿",
    ":syringe:": "👷‍♀️",
    ":pill:": "👷‍♂️",
    ":kiss:": "👷",
    ":love_letter:": "👸🏻",
    ":ring:": "👸🏼",
    ":gem:": "👸🏽",
    ":couplekiss:": "👸🏾",
    ":bouquet:": "👸🏿",
    ":couple_with_heart:": "👸",
    ":wedding:": "👹",
    ":heartbeat:": "👺",
    ":broken_heart:": "👻",
    ":two_hearts:": "👼🏻",
    ":sparkling_heart:": "👼🏼",
    ":heartpulse:": "👼🏽",
    ":cupid:": "👼🏾",
    ":blue_heart:": "👼🏿",
    ":green_heart:": "👼",
    ":yellow_heart:": "👽",
    ":purple_heart:": "👾",
    ":gift_heart:": "👿",
    ":revolving_hearts:": "💀",
    ":heart_decoration:": "💁🏻‍♀️",
    ":diamond_shape_with_a_dot_inside:": "💁🏻‍♂️",
    ":bulb:": "💁🏻",
    ":anger:": "💁🏼‍♀️",
    ":bomb:": "💁🏼‍♂️",
    ":zzz:": "💁🏼",
    ":boom:": "💁🏽‍♀️",
    ":sweat_drops:": "💁🏽‍♂️",
    ":droplet:": "💁🏽",
    ":dash:": "💁🏾‍♀️",
    ":poop:": "💁🏾‍♂️",
    ":muscle_tone1:": "💁🏾",
    ":muscle_tone2:": "💁🏿‍♀️",
    ":muscle_tone3:": "💁🏿‍♂️",
    ":muscle_tone4:": "💁🏿",
    ":muscle_tone5:": "💁‍♀️",
    ":muscle:": "💁‍♂️",
    ":dizzy:": "💁",
    ":speech_balloon:": "💂🏻‍♀️",
    ":thought_balloon:": "💂🏻‍♂️",
    ":white_flower:": "💂🏻",
    ":100:": "💂🏼‍♀️",
    ":moneybag:": "💂🏼‍♂️",
    ":currency_exchange:": "💂🏼",
    ":heavy_dollar_sign:": "💂🏽‍♀️",
    ":credit_card:": "💂🏽‍♂️",
    ":yen:": "💂🏽",
    ":dollar:": "💂🏾‍♀️",
    ":euro:": "💂🏾‍♂️",
    ":pound:": "💂🏾",
    ":money_with_wings:": "💂🏿‍♀️",
    ":chart:": "💂🏿‍♂️",
    ":seat:": "💂🏿",
    ":computer:": "💂‍♀️",
    ":briefcase:": "💂‍♂️",
    ":minidisc:": "💂",
    ":floppy_disk:": "💃🏻",
    ":cd:": "💃🏼",
    ":dvd:": "💃🏽",
    ":file_folder:": "💃🏾",
    ":open_file_folder:": "💃🏿",
    ":page_with_curl:": "💃",
    ":page_facing_up:": "💄",
    ":date:": "💅🏻",
    ":calendar:": "💅🏼",
    ":card_index:": "💅🏽",
    ":chart_with_upwards_trend:": "💅🏾",
    ":chart_with_downwards_trend:": "💅🏿",
    ":bar_chart:": "💅",
    ":clipboard:": "💆🏻‍♀️",
    ":pushpin:": "💆🏻‍♂️",
    ":round_pushpin:": "💆🏻",
    ":paperclip:": "💆🏼‍♀️",
    ":straight_ruler:": "💆🏼‍♂️",
    ":triangular_ruler:": "💆🏼",
    ":bookmark_tabs:": "💆🏽‍♀️",
    ":ledger:": "💆🏽‍♂️",
    ":notebook:": "💆🏽",
    ":notebook_with_decorative_cover:": "💆🏾‍♀️",
    ":closed_book:": "💆🏾‍♂️",
    ":book:": "💆🏾",
    ":green_book:": "💆🏿‍♀️",
    ":blue_book:": "💆🏿‍♂️",
    ":orange_book:": "💆🏿",
    ":books:": "💆‍♀️",
    ":name_badge:": "💆‍♂️",
    ":scroll:": "💆",
    ":pencil:": "💇🏻‍♀️",
    ":telephone_receiver:": "💇🏻‍♂️",
    ":pager:": "💇🏻",
    ":fax:": "💇🏼‍♀️",
    ":satellite:": "💇🏼‍♂️",
    ":loudspeaker:": "💇🏼",
    ":mega:": "💇🏽‍♀️",
    ":outbox_tray:": "💇🏽‍♂️",
    ":inbox_tray:": "💇🏽",
    ":package:": "💇🏾‍♀️",
    ":e-mail:": "💇🏾‍♂️",
    ":incoming_envelope:": "💇🏾",
    ":envelope_with_arrow:": "💇🏿‍♀️",
    ":mailbox_closed:": "💇🏿‍♂️",
    ":mailbox:": "💇🏿",
    ":mailbox_with_mail:": "💇‍♀️",
    ":mailbox_with_no_mail:": "💇‍♂️",
    ":postbox:": "💇",
    ":postal_horn:": "💈",
    ":newspaper:": "💉",
    ":iphone:": "💊",
    ":calling:": "💋",
    ":vibration_mode:": "💌",
    ":mobile_phone_off:": "💍",
    ":no_mobile_phones:": "💎",
    ":signal_strength:": "💏",
    ":camera:": "💐",
    ":camera_with_flash:": "💑",
    ":video_camera:": "💒",
    ":tv:": "💓",
    ":radio:": "💔",
    ":vhs:": "💕",
    ":projector:": "💖",
    ":prayer_beads:": "💗",
    ":twisted_rightwards_arrows:": "💘",
    ":repeat:": "💙",
    ":repeat_one:": "💚",
    ":arrows_clockwise:": "💛",
    ":arrows_counterclockwise:": "💜",
    ":low_brightness:": "💝",
    ":high_brightness:": "💞",
    ":mute:": "💟",
    ":speaker:": "💠",
    ":sound:": "💡",
    ":loud_sound:": "💢",
    ":battery:": "💣",
    ":electric_plug:": "💤",
    ":mag:": "💥",
    ":mag_right:": "💦",
    ":lock_with_ink_pen:": "💧",
    ":closed_lock_with_key:": "💨",
    ":key:": "💩",
    ":lock:": "💪🏻",
    ":unlock:": "💪🏼",
    ":bell:": "💪🏽",
    ":no_bell:": "💪🏾",
    ":bookmark:": "💪🏿",
    ":link:": "💪",
    ":radio_button:": "💫",
    ":back:": "💬",
    ":end:": "💭",
    ":on:": "💮",
    ":soon:": "💯",
    ":top:": "💰",
    ":underage:": "💱",
    ":keycap_ten:": "💲",
    ":capital_abcd:": "💳",
    ":abcd:": "💴",
    ":1234:": "💵",
    ":symbols:": "💶",
    ":abc:": "💷",
    ":fire:": "💸",
    ":flashlight:": "💹",
    ":wrench:": "💺",
    ":hammer:": "💻",
    ":nut_and_bolt:": "💼",
    ":knife:": "💽",
    ":gun:": "💾",
    ":microscope:": "💿",
    ":telescope:": "📀",
    ":crystal_ball:": "📁",
    ":six_pointed_star:": "📂",
    ":beginner:": "📃",
    ":trident:": "📄",
    ":black_square_button:": "📅",
    ":white_square_button:": "📆",
    ":red_circle:": "📇",
    ":large_blue_circle:": "📈",
    ":large_orange_diamond:": "📉",
    ":large_blue_diamond:": "📊",
    ":small_orange_diamond:": "📋",
    ":small_blue_diamond:": "📌",
    ":small_red_triangle:": "📍",
    ":small_red_triangle_down:": "📎",
    ":arrow_up_small:": "📏",
    ":arrow_down_small:": "📐",
    ":om_symbol:": "📑",
    ":dove:": "📒",
    ":kaaba:": "📓",
    ":mosque:": "📔",
    ":synagogue:": "📕",
    ":menorah:": "📖",
    ":clock1:": "📗",
    ":clock2:": "📘",
    ":clock3:": "📙",
    ":clock4:": "📚",
    ":clock5:": "📛",
    ":clock6:": "📜",
    ":clock7:": "📝",
    ":clock8:": "📞",
    ":clock9:": "📟",
    ":clock10:": "📠",
    ":clock11:": "📡",
    ":clock12:": "📢",
    ":clock130:": "📣",
    ":clock230:": "📤",
    ":clock330:": "📥",
    ":clock430:": "📦",
    ":clock530:": "📧",
    ":clock630:": "📨",
    ":clock730:": "📩",
    ":clock830:": "📪",
    ":clock930:": "📫",
    ":clock1030:": "📬",
    ":clock1130:": "📭",
    ":clock1230:": "📮",
    ":candle:": "📯",
    ":clock:": "📰",
    ":hole:": "📱",
    ":levitate::tone1:": "📲",
    ":levitate::tone2:": "📳",
    ":levitate::tone3:": "📴",
    ":levitate::tone4:": "📵",
    ":levitate::tone5:": "📶",
    ":levitate:": "📷",
    ":spy_tone1:‍♀️": "📸",
    ":spy_tone1:‍♂️": "📹",
    ":spy_tone1:": "📺",
    ":spy_tone2:‍♀️": "📻",
    ":spy_tone2:‍♂️": "📼",
    ":spy_tone2:": "📽️",
    ":spy_tone3:‍♀️": "📿",
    ":spy_tone3:‍♂️": "🔀",
    ":spy_tone3:": "🔁",
    ":spy_tone4:‍♀️": "🔂",
    ":spy_tone4:‍♂️": "🔃",
    ":spy_tone4:": "🔄",
    ":spy_tone5:‍♀️": "🔅",
    ":spy_tone5:‍♂️": "🔆",
    ":spy_tone5:": "🔇",
    ":spy:‍♀️": "🔈",
    ":spy:‍♂️": "🔉",
    ":spy:": "🔊",
    ":dark_sunglasses:": "🔋",
    ":spider:": "🔌",
    ":spider_web:": "🔍",
    ":joystick:": "🔎",
    ":man_dancing_tone1:": "🔏",
    ":man_dancing_tone2:": "🔐",
    ":man_dancing_tone3:": "🔑",
    ":man_dancing_tone4:": "🔒",
    ":man_dancing_tone5:": "🔓",
    ":man_dancing:": "🔔",
    ":paperclips:": "🔕",
    ":pen_ballpoint:": "🔖",
    ":pen_fountain:": "🔗",
    ":paintbrush:": "🔘",
    ":crayon:": "🔙",
    ":hand_splayed_tone1:": "🔚",
    ":hand_splayed_tone2:": "🔛",
    ":hand_splayed_tone3:": "🔜",
    ":hand_splayed_tone4:": "🔝",
    ":hand_splayed_tone5:": "🔞",
    ":hand_splayed:": "🔟",
    ":middle_finger_tone1:": "🔠",
    ":middle_finger_tone2:": "🔡",
    ":middle_finger_tone3:": "🔢",
    ":middle_finger_tone4:": "🔣",
    ":middle_finger_tone5:": "🔤",
    ":middle_finger:": "🔥",
    ":vulcan_tone1:": "🔦",
    ":vulcan_tone2:": "🔧",
    ":vulcan_tone3:": "🔨",
    ":vulcan_tone4:": "🔩",
    ":vulcan_tone5:": "🔪",
    ":vulcan:": "🔫",
    ":black_heart:": "🔬",
    ":desktop:": "🔭",
    ":printer:": "🔮",
    ":mouse_three_button:": "🔯",
    ":trackball:": "🔰",
    ":frame_photo:": "🔱",
    ":dividers:": "🔲",
    ":card_box:": "🔳",
    ":file_cabinet:": "🔴",
    ":wastebasket:": "🔵",
    ":notepad_spiral:": "🔶",
    ":calendar_spiral:": "🔷",
    ":compression:": "🔸",
    ":key2:": "🔹",
    ":newspaper2:": "🔺",
    ":dagger:": "🔻",
    ":speaking_head:": "🔼",
    ":speech_left:": "🔽",
    ":anger_right:": "🕉️",
    ":ballot_box:": "🕊️",
    ":map:": "🕋",
    ":mount_fuji:": "🕌",
    ":tokyo_tower:": "🕍",
    ":statue_of_liberty:": "🕎",
    ":japan:": "🕐",
    ":moyai:": "🕑",
    ":grinning:": "🕒",
    ":grin:": "🕓",
    ":joy:": "🕔",
    ":smiley:": "🕕",
    ":smile:": "🕖",
    ":sweat_smile:": "🕗",
    ":laughing:": "🕘",
    ":innocent:": "🕙",
    ":smiling_imp:": "🕚",
    ":wink:": "🕛",
    ":blush:": "🕜",
    ":yum:": "🕝",
    ":relieved:": "🕞",
    ":heart_eyes:": "🕟",
    ":sunglasses:": "🕠",
    ":smirk:": "🕡",
    ":neutral_face:": "🕢",
    ":expressionless:": "🕣",
    ":unamused:": "🕤",
    ":sweat:": "🕥",
    ":pensive:": "🕦",
    ":confused:": "🕧",
    ":confounded:": "🕯️",
    ":kissing:": "🕰️",
    ":kissing_heart:": "🕳️",
    ":kissing_smiling_eyes:": "🕴🏻‍♀️",
    ":kissing_closed_eyes:": "🕴🏻‍♂️",
    ":stuck_out_tongue:": "🕴🏻",
    ":stuck_out_tongue_winking_eye:": "🕴🏼‍♀️",
    ":stuck_out_tongue_closed_eyes:": "🕴🏼‍♂️",
    ":disappointed:": "🕴🏼",
    ":worried:": "🕴🏽‍♀️",
    ":angry:": "🕴🏽‍♂️",
    ":rage:": "🕴🏽",
    ":cry:": "🕴🏾‍♀️",
    ":persevere:": "🕴🏾‍♂️",
    ":triumph:": "🕴🏾",
    ":disappointed_relieved:": "🕴🏿‍♀️",
    ":frowning:": "🕴🏿‍♂️",
    ":anguished:": "🕴🏿",
    ":fearful:": "🕴️‍♀️",
    ":weary:": "🕴️‍♂️",
    ":sleepy:": "🕴️",
    ":tired_face:": "🕵🏻‍♀️",
    ":grimacing:": "🕵🏻‍♂️",
    ":sob:": "🕵🏻",
    ":open_mouth:": "🕵🏼‍♀️",
    ":hushed:": "🕵🏼‍♂️",
    ":cold_sweat:": "🕵🏼",
    ":scream:": "🕵🏽‍♀️",
    ":astonished:": "🕵🏽‍♂️",
    ":flushed:": "🕵🏽",
    ":sleeping:": "🕵🏾‍♀️",
    ":dizzy_face:": "🕵🏾‍♂️",
    ":no_mouth:": "🕵🏾",
    ":mask:": "🕵🏿‍♀️",
    ":smile_cat:": "🕵🏿‍♂️",
    ":joy_cat:": "🕵🏿",
    ":smiley_cat:": "🕵️‍♀️",
    ":heart_eyes_cat:": "🕵️‍♂️",
    ":smirk_cat:": "🕵️",
    ":kissing_cat:": "🕶️",
    ":pouting_cat:": "🕷️",
    ":crying_cat_face:": "🕸️",
    ":scream_cat:": "🕹️",
    ":slight_frown:": "🕺🏻",
    ":slight_smile:": "🕺🏼",
    ":upside_down:": "🕺🏽",
    ":rolling_eyes:": "🕺🏾",
    ":no_good_tone1:‍♀️": "🕺🏿",
    ":no_good_tone1:‍♂️": "🕺",
    ":no_good_tone1:": "🖇️",
    ":no_good_tone2:‍♀️": "🖊️",
    ":no_good_tone2:‍♂️": "🖋️",
    ":no_good_tone2:": "🖌️",
    ":no_good_tone3:‍♀️": "🖍️",
    ":no_good_tone3:‍♂️": "🖐🏻",
    ":no_good_tone3:": "🖐🏼",
    ":no_good_tone4:‍♀️": "🖐🏽",
    ":no_good_tone4:‍♂️": "🖐🏾",
    ":no_good_tone4:": "🖐🏿",
    ":no_good_tone5:‍♀️": "🖐️",
    ":no_good_tone5:‍♂️": "🖕🏻",
    ":no_good_tone5:": "🖕🏼",
    ":no_good:‍♀️": "🖕🏽",
    ":no_good:‍♂️": "🖕🏾",
    ":no_good:": "🖕🏿",
    ":ok_woman_tone1:‍♀️": "🖕",
    ":ok_woman_tone1:‍♂️": "🖖🏻",
    ":ok_woman_tone1:": "🖖🏼",
    ":ok_woman_tone2:‍♀️": "🖖🏽",
    ":ok_woman_tone2:‍♂️": "🖖🏾",
    ":ok_woman_tone2:": "🖖🏿",
    ":ok_woman_tone3:‍♀️": "🖖",
    ":ok_woman_tone3:‍♂️": "🖤",
    ":ok_woman_tone3:": "🖥️",
    ":ok_woman_tone4:‍♀️": "🖨️",
    ":ok_woman_tone4:‍♂️": "🖱️",
    ":ok_woman_tone4:": "🖲️",
    ":ok_woman_tone5:‍♀️": "🖼️",
    ":ok_woman_tone5:‍♂️": "🗂️",
    ":ok_woman_tone5:": "🗃️",
    ":ok_woman:‍♀️": "🗄️",
    ":ok_woman:‍♂️": "🗑️",
    ":ok_woman:": "🗒️",
    ":bow_tone1:‍♀️": "🗓️",
    ":bow_tone1:‍♂️": "🗜️",
    ":bow_tone1:": "🗝️",
    ":bow_tone2:‍♀️": "🗞️",
    ":bow_tone2:‍♂️": "🗡️",
    ":bow_tone2:": "🗣️",
    ":bow_tone3:‍♀️": "🗨️",
    ":bow_tone3:‍♂️": "🗯️",
    ":bow_tone3:": "🗳️",
    ":bow_tone4:‍♀️": "🗺️",
    ":bow_tone4:‍♂️": "🗻",
    ":bow_tone4:": "🗼",
    ":bow_tone5:‍♀️": "🗽",
    ":bow_tone5:‍♂️": "🗾",
    ":bow_tone5:": "🗿",
    ":bow:‍♀️": "😀",
    ":bow:‍♂️": "😁",
    ":bow:": "😂",
    ":see_no_evil:": "😃",
    ":hear_no_evil:": "😄",
    ":speak_no_evil:": "😅",
    ":raising_hand_tone1:‍♀️": "😆",
    ":raising_hand_tone1:‍♂️": "😇",
    ":raising_hand_tone1:": "😈",
    ":raising_hand_tone2:‍♀️": "😉",
    ":raising_hand_tone2:‍♂️": "😊",
    ":raising_hand_tone2:": "😋",
    ":raising_hand_tone3:‍♀️": "😌",
    ":raising_hand_tone3:‍♂️": "😍",
    ":raising_hand_tone3:": "😎",
    ":raising_hand_tone4:‍♀️": "😏",
    ":raising_hand_tone4:‍♂️": "😐",
    ":raising_hand_tone4:": "😑",
    ":raising_hand_tone5:‍♀️": "😒",
    ":raising_hand_tone5:‍♂️": "😓",
    ":raising_hand_tone5:": "😔",
    ":raising_hand:‍♀️": "😕",
    ":raising_hand:‍♂️": "😖",
    ":raising_hand:": "😗",
    ":raised_hands_tone1:": "😘",
    ":raised_hands_tone2:": "😙",
    ":raised_hands_tone3:": "😚",
    ":raised_hands_tone4:": "😛",
    ":raised_hands_tone5:": "😜",
    ":raised_hands:": "😝",
    ":person_frowning_tone1:‍♀️": "😞",
    ":person_frowning_tone1:‍♂️": "😟",
    ":person_frowning_tone1:": "😠",
    ":person_frowning_tone2:‍♀️": "😡",
    ":person_frowning_tone2:‍♂️": "😢",
    ":person_frowning_tone2:": "😣",
    ":person_frowning_tone3:‍♀️": "😤",
    ":person_frowning_tone3:‍♂️": "😥",
    ":person_frowning_tone3:": "😦",
    ":person_frowning_tone4:‍♀️": "😧",
    ":person_frowning_tone4:‍♂️": "😨",
    ":person_frowning_tone4:": "😩",
    ":person_frowning_tone5:‍♀️": "😪",
    ":person_frowning_tone5:‍♂️": "😫",
    ":person_frowning_tone5:": "😬",
    ":person_frowning:‍♀️": "😭",
    ":person_frowning:‍♂️": "😮",
    ":person_frowning:": "😯",
    ":person_with_pouting_face_tone1:‍♀️": "😰",
    ":person_with_pouting_face_tone1:‍♂️": "😱",
    ":person_with_pouting_face_tone1:": "😲",
    ":person_with_pouting_face_tone2:‍♀️": "😳",
    ":person_with_pouting_face_tone2:‍♂️": "😴",
    ":person_with_pouting_face_tone2:": "😵",
    ":person_with_pouting_face_tone3:‍♀️": "😶",
    ":person_with_pouting_face_tone3:‍♂️": "😷",
    ":person_with_pouting_face_tone3:": "😸",
    ":person_with_pouting_face_tone4:‍♀️": "😹",
    ":person_with_pouting_face_tone4:‍♂️": "😺",
    ":person_with_pouting_face_tone4:": "😻",
    ":person_with_pouting_face_tone5:‍♀️": "😼",
    ":person_with_pouting_face_tone5:‍♂️": "😽",
    ":person_with_pouting_face_tone5:": "😾",
    ":person_with_pouting_face:‍♀️": "😿",
    ":person_with_pouting_face:‍♂️": "🙀",
    ":person_with_pouting_face:": "🙁",
    ":pray_tone1:": "🙂",
    ":pray_tone2:": "🙃",
    ":pray_tone3:": "🙄",
    ":pray_tone4:": "🙅🏻‍♀️",
    ":pray_tone5:": "🙅🏻‍♂️",
    ":pray:": "🙅🏻",
    ":rocket:": "🙅🏼‍♀️",
    ":helicopter:": "🙅🏼‍♂️",
    ":steam_locomotive:": "🙅🏼",
    ":railway_car:": "🙅🏽‍♀️",
    ":bullettrain_side:": "🙅🏽‍♂️",
    ":bullettrain_front:": "🙅🏽",
    ":train2:": "🙅🏾‍♀️",
    ":metro:": "🙅🏾‍♂️",
    ":light_rail:": "🙅🏾",
    ":station:": "🙅🏿‍♀️",
    ":tram:": "🙅🏿‍♂️",
    ":train:": "🙅🏿",
    ":bus:": "🙅‍♀️",
    ":oncoming_bus:": "🙅‍♂️",
    ":trolleybus:": "🙅",
    ":busstop:": "🙆🏻‍♀️",
    ":minibus:": "🙆🏻‍♂️",
    ":ambulance:": "🙆🏻",
    ":fire_engine:": "🙆🏼‍♀️",
    ":police_car:": "🙆🏼‍♂️",
    ":oncoming_police_car:": "🙆🏼",
    ":taxi:": "🙆🏽‍♀️",
    ":oncoming_taxi:": "🙆🏽‍♂️",
    ":red_car:": "🙆🏽",
    ":oncoming_automobile:": "🙆🏾‍♀️",
    ":blue_car:": "🙆🏾‍♂️",
    ":truck:": "🙆🏾",
    ":articulated_lorry:": "🙆🏿‍♀️",
    ":tractor:": "🙆🏿‍♂️",
    ":monorail:": "🙆🏿",
    ":mountain_railway:": "🙆‍♀️",
    ":suspension_railway:": "🙆‍♂️",
    ":mountain_cableway:": "🙆",
    ":aerial_tramway:": "🙇🏻‍♀️",
    ":ship:": "🙇🏻‍♂️",
    ":rowboat_tone1:‍♀️": "🙇🏻",
    ":rowboat_tone1:‍♂️": "🙇🏼‍♀️",
    ":rowboat_tone1:": "🙇🏼‍♂️",
    ":rowboat_tone2:‍♀️": "🙇🏼",
    ":rowboat_tone2:‍♂️": "🙇🏽‍♀️",
    ":rowboat_tone2:": "🙇🏽‍♂️",
    ":rowboat_tone3:‍♀️": "🙇🏽",
    ":rowboat_tone3:‍♂️": "🙇🏾‍♀️",
    ":rowboat_tone3:": "🙇🏾‍♂️",
    ":rowboat_tone4:‍♀️": "🙇🏾",
    ":rowboat_tone4:‍♂️": "🙇🏿‍♀️",
    ":rowboat_tone4:": "🙇🏿‍♂️",
    ":rowboat_tone5:‍♀️": "🙇🏿",
    ":rowboat_tone5:‍♂️": "🙇‍♀️",
    ":rowboat_tone5:": "🙇‍♂️",
    ":rowboat:‍♀️": "🙇",
    ":rowboat:‍♂️": "🙈",
    ":rowboat:": "🙉",
    ":speedboat:": "🙊",
    ":traffic_light:": "🙋🏻‍♀️",
    ":vertical_traffic_light:": "🙋🏻‍♂️",
    ":construction:": "🙋🏻",
    ":rotating_light:": "🙋🏼‍♀️",
    ":triangular_flag_on_post:": "🙋🏼‍♂️",
    ":door:": "🙋🏼",
    ":no_entry_sign:": "🙋🏽‍♀️",
    ":smoking:": "🙋🏽‍♂️",
    ":no_smoking:": "🙋🏽",
    ":put_litter_in_its_place:": "🙋🏾‍♀️",
    ":do_not_litter:": "🙋🏾‍♂️",
    ":potable_water:": "🙋🏾",
    ":non-potable_water:": "🙋🏿‍♀️",
    ":bike:": "🙋🏿‍♂️",
    ":no_bicycles:": "🙋🏿",
    ":bicyclist_tone1:‍♀️": "🙋‍♀️",
    ":bicyclist_tone1:‍♂️": "🙋‍♂️",
    ":bicyclist_tone1:": "🙋",
    ":bicyclist_tone2:‍♀️": "🙌🏻",
    ":bicyclist_tone2:‍♂️": "🙌🏼",
    ":bicyclist_tone2:": "🙌🏽",
    ":bicyclist_tone3:‍♀️": "🙌🏾",
    ":bicyclist_tone3:‍♂️": "🙌🏿",
    ":bicyclist_tone3:": "🙌",
    ":bicyclist_tone4:‍♀️": "🙍🏻‍♀️",
    ":bicyclist_tone4:‍♂️": "🙍🏻‍♂️",
    ":bicyclist_tone4:": "🙍🏻",
    ":bicyclist_tone5:‍♀️": "🙍🏼‍♀️",
    ":bicyclist_tone5:‍♂️": "🙍🏼‍♂️",
    ":bicyclist_tone5:": "🙍🏼",
    ":bicyclist:‍♀️": "🙍🏽‍♀️",
    ":bicyclist:‍♂️": "🙍🏽‍♂️",
    ":bicyclist:": "🙍🏽",
    ":mountain_bicyclist_tone1:‍♀️": "🙍🏾‍♀️",
    ":mountain_bicyclist_tone1:‍♂️": "🙍🏾‍♂️",
    ":mountain_bicyclist_tone1:": "🙍🏾",
    ":mountain_bicyclist_tone2:‍♀️": "🙍🏿‍♀️",
    ":mountain_bicyclist_tone2:‍♂️": "🙍🏿‍♂️",
    ":mountain_bicyclist_tone2:": "🙍🏿",
    ":mountain_bicyclist_tone3:‍♀️": "🙍‍♀️",
    ":mountain_bicyclist_tone3:‍♂️": "🙍‍♂️",
    ":mountain_bicyclist_tone3:": "🙍",
    ":mountain_bicyclist_tone4:‍♀️": "🙎🏻‍♀️",
    ":mountain_bicyclist_tone4:‍♂️": "🙎🏻‍♂️",
    ":mountain_bicyclist_tone4:": "🙎🏻",
    ":mountain_bicyclist_tone5:‍♀️": "🙎🏼‍♀️",
    ":mountain_bicyclist_tone5:‍♂️": "🙎🏼‍♂️",
    ":mountain_bicyclist_tone5:": "🙎🏼",
    ":mountain_bicyclist:‍♀️": "🙎🏽‍♀️",
    ":mountain_bicyclist:‍♂️": "🙎🏽‍♂️",
    ":mountain_bicyclist:": "🙎🏽",
    ":walking_tone1:‍♀️": "🙎🏾‍♀️",
    ":walking_tone1:‍♂️": "🙎🏾‍♂️",
    ":walking_tone1:": "🙎🏾",
    ":walking_tone2:‍♀️": "🙎🏿‍♀️",
    ":walking_tone2:‍♂️": "🙎🏿‍♂️",
    ":walking_tone2:": "🙎🏿",
    ":walking_tone3:‍♀️": "🙎‍♀️",
    ":walking_tone3:‍♂️": "🙎‍♂️",
    ":walking_tone3:": "🙎",
    ":walking_tone4:‍♀️": "🙏🏻",
    ":walking_tone4:‍♂️": "🙏🏼",
    ":walking_tone4:": "🙏🏽",
    ":walking_tone5:‍♀️": "🙏🏾",
    ":walking_tone5:‍♂️": "🙏🏿",
    ":walking_tone5:": "🙏",
    ":walking:‍♀️": "🚀",
    ":walking:‍♂️": "🚁",
    ":walking:": "🚂",
    ":no_pedestrians:": "🚃",
    ":children_crossing:": "🚄",
    ":mens:": "🚅",
    ":womens:": "🚆",
    ":restroom:": "🚇",
    ":baby_symbol:": "🚈",
    ":toilet:": "🚉",
    ":wc:": "🚊",
    ":shower:": "🚋",
    ":bath_tone1:": "🚌",
    ":bath_tone2:": "🚍",
    ":bath_tone3:": "🚎",
    ":bath_tone4:": "🚏",
    ":bath_tone5:": "🚐",
    ":bath:": "🚑",
    ":bathtub:": "🚒",
    ":passport_control:": "🚓",
    ":customs:": "🚔",
    ":baggage_claim:": "🚕",
    ":left_luggage:": "🚖",
    ":couch:": "🚗",
    ":sleeping_accommodation::tone1:": "🚘",
    ":sleeping_accommodation::tone2:": "🚙",
    ":sleeping_accommodation::tone3:": "🚚",
    ":sleeping_accommodation::tone4:": "🚛",
    ":sleeping_accommodation::tone5:": "🚜",
    ":sleeping_accommodation:": "🚝",
    ":shopping_bags:": "🚞",
    ":bellhop:": "🚟",
    ":bed:": "🚠",
    ":place_of_worship:": "🚡",
    ":octagonal_sign:": "🚢",
    ":shopping_cart:": "🚣🏻‍♀️",
    ":tools:": "🚣🏻‍♂️",
    ":shield:": "🚣🏻",
    ":oil:": "🚣🏼‍♀️",
    ":motorway:": "🚣🏼‍♂️",
    ":railway_track:": "🚣🏼",
    ":motorboat:": "🚣🏽‍♀️",
    ":airplane_small:": "🚣🏽‍♂️",
    ":airplane_departure:": "🚣🏽",
    ":airplane_arriving:": "🚣🏾‍♀️",
    ":satellite_orbital:": "🚣🏾‍♂️",
    ":cruise_ship:": "🚣🏾",
    ":scooter:": "🚣🏿‍♀️",
    ":motor_scooter:": "🚣🏿‍♂️",
    ":canoe:": "🚣🏿",
    ":zipper_mouth:": "🚣‍♀️",
    ":money_mouth:": "🚣‍♂️",
    ":thermometer_face:": "🚣",
    ":nerd:": "🚤",
    ":thinking:": "🚥",
    ":head_bandage:": "🚦",
    ":robot:": "🚧",
    ":hugging:": "🚨",
    ":metal_tone1:": "🚩",
    ":metal_tone2:": "🚪",
    ":metal_tone3:": "🚫",
    ":metal_tone4:": "🚬",
    ":metal_tone5:": "🚭",
    ":metal:": "🚮",
    ":call_me_tone1:": "🚯",
    ":call_me_tone2:": "🚰",
    ":call_me_tone3:": "🚱",
    ":call_me_tone4:": "🚲",
    ":call_me_tone5:": "🚳",
    ":call_me:": "🚴🏻‍♀️",
    ":raised_back_of_hand_tone1:": "🚴🏻‍♂️",
    ":raised_back_of_hand_tone2:": "🚴🏻",
    ":raised_back_of_hand_tone3:": "🚴🏼‍♀️",
    ":raised_back_of_hand_tone4:": "🚴🏼‍♂️",
    ":raised_back_of_hand_tone5:": "🚴🏼",
    ":raised_back_of_hand:": "🚴🏽‍♀️",
    ":left_facing_fist_tone1:": "🚴🏽‍♂️",
    ":left_facing_fist_tone2:": "🚴🏽",
    ":left_facing_fist_tone3:": "🚴🏾‍♀️",
    ":left_facing_fist_tone4:": "🚴🏾‍♂️",
    ":left_facing_fist_tone5:": "🚴🏾",
    ":left_facing_fist:": "🚴🏿‍♀️",
    ":right_facing_fist_tone1:": "🚴🏿‍♂️",
    ":right_facing_fist_tone2:": "🚴🏿",
    ":right_facing_fist_tone3:": "🚴‍♀️",
    ":right_facing_fist_tone4:": "🚴‍♂️",
    ":right_facing_fist_tone5:": "🚴",
    ":right_facing_fist:": "🚵🏻‍♀️",
    ":handshake_tone1:": "🚵🏻‍♂️",
    ":handshake_tone2:": "🚵🏻",
    ":handshake_tone3:": "🚵🏼‍♀️",
    ":handshake_tone4:": "🚵🏼‍♂️",
    ":handshake_tone5:": "🚵🏼",
    ":handshake:": "🚵🏽‍♀️",
    ":fingers_crossed_tone1:": "🚵🏽‍♂️",
    ":fingers_crossed_tone2:": "🚵🏽",
    ":fingers_crossed_tone3:": "🚵🏾‍♀️",
    ":fingers_crossed_tone4:": "🚵🏾‍♂️",
    ":fingers_crossed_tone5:": "🚵🏾",
    ":fingers_crossed:": "🚵🏿‍♀️",
    ":cowboy:": "🚵🏿‍♂️",
    ":clown:": "🚵🏿",
    ":nauseated_face:": "🚵‍♀️",
    ":rofl:": "🚵‍♂️",
    ":drooling_face:": "🚵",
    ":lying_face:": "🚶🏻‍♀️",
    ":face_palm_tone1:‍♀️": "🚶🏻‍♂️",
    ":face_palm_tone1:‍♂️": "🚶🏻",
    ":face_palm_tone1:": "🚶🏼‍♀️",
    ":face_palm_tone2:‍♀️": "🚶🏼‍♂️",
    ":face_palm_tone2:‍♂️": "🚶🏼",
    ":face_palm_tone2:": "🚶🏽‍♀️",
    ":face_palm_tone3:‍♀️": "🚶🏽‍♂️",
    ":face_palm_tone3:‍♂️": "🚶🏽",
    ":face_palm_tone3:": "🚶🏾‍♀️",
    ":face_palm_tone4:‍♀️": "🚶🏾‍♂️",
    ":face_palm_tone4:‍♂️": "🚶🏾",
    ":face_palm_tone4:": "🚶🏿‍♀️",
    ":face_palm_tone5:‍♀️": "🚶🏿‍♂️",
    ":face_palm_tone5:‍♂️": "🚶🏿",
    ":face_palm_tone5:": "🚶‍♀️",
    ":face_palm:‍♀️": "🚶‍♂️",
    ":face_palm:‍♂️": "🚶",
    ":face_palm:": "🚷",
    ":sneezing_face:": "🚸",
    ":pregnant_woman_tone1:": "🚹",
    ":pregnant_woman_tone2:": "🚺",
    ":pregnant_woman_tone3:": "🚻",
    ":pregnant_woman_tone4:": "🚼",
    ":pregnant_woman_tone5:": "🚽",
    ":pregnant_woman:": "🚾",
    ":selfie_tone1:": "🚿",
    ":selfie_tone2:": "🛀🏻",
    ":selfie_tone3:": "🛀🏼",
    ":selfie_tone4:": "🛀🏽",
    ":selfie_tone5:": "🛀🏾",
    ":selfie:": "🛀🏿",
    ":prince_tone1:": "🛀",
    ":prince_tone2:": "🛁",
    ":prince_tone3:": "🛂",
    ":prince_tone4:": "🛃",
    ":prince_tone5:": "🛄",
    ":prince:": "🛅",
    ":man_in_tuxedo_tone1:": "🛋️",
    ":man_in_tuxedo_tone2:": "🛌🏻",
    ":man_in_tuxedo_tone3:": "🛌🏼",
    ":man_in_tuxedo_tone4:": "🛌🏽",
    ":man_in_tuxedo_tone5:": "🛌🏾",
    ":man_in_tuxedo:": "🛌🏿",
    ":mrs_claus_tone1:": "🛌",
    ":mrs_claus_tone2:": "🛍️",
    ":mrs_claus_tone3:": "🛎️",
    ":mrs_claus_tone4:": "🛏️",
    ":mrs_claus_tone5:": "🛐",
    ":mrs_claus:": "🛑",
    ":shrug_tone1:‍♀️": "🛒",
    ":shrug_tone1:‍♂️": "🛕",
    ":shrug_tone1:": "🛠️",
    ":shrug_tone2:‍♀️": "🛡️",
    ":shrug_tone2:‍♂️": "🛢️",
    ":shrug_tone2:": "🛣️",
    ":shrug_tone3:‍♀️": "🛤️",
    ":shrug_tone3:‍♂️": "🛥️",
    ":shrug_tone3:": "🛩️",
    ":shrug_tone4:‍♀️": "🛫",
    ":shrug_tone4:‍♂️": "🛬",
    ":shrug_tone4:": "🛰️",
    ":shrug_tone5:‍♀️": "🛳️",
    ":shrug_tone5:‍♂️": "🛴",
    ":shrug_tone5:": "🛵",
    ":shrug:‍♀️": "🛶",
    ":shrug:‍♂️": "🛷",
    ":shrug:": "🛸",
    ":cartwheel_tone1:‍♀️": "🛹",
    ":cartwheel_tone1:‍♂️": "🛺",
    ":cartwheel_tone1:": "🟠",
    ":cartwheel_tone2:‍♀️": "🟡",
    ":cartwheel_tone2:‍♂️": "🟢",
    ":cartwheel_tone2:": "🟣",
    ":cartwheel_tone3:‍♀️": "🟤",
    ":cartwheel_tone3:‍♂️": "🟥",
    ":cartwheel_tone3:": "🟦",
    ":cartwheel_tone4:‍♀️": "🟧",
    ":cartwheel_tone4:‍♂️": "🟨",
    ":cartwheel_tone4:": "🟩",
    ":cartwheel_tone5:‍♀️": "🟪",
    ":cartwheel_tone5:‍♂️": "🟫",
    ":cartwheel_tone5:": "🤍",
    ":cartwheel:‍♀️": "🤎",
    ":cartwheel:‍♂️": "🤏🏻",
    ":cartwheel:": "🤏🏼",
    ":juggling_tone1:‍♀️": "🤏🏽",
    ":juggling_tone1:‍♂️": "🤏🏾",
    ":juggling_tone1:": "🤏🏿",
    ":juggling_tone2:‍♀️": "🤏",
    ":juggling_tone2:‍♂️": "🤐",
    ":juggling_tone2:": "🤑",
    ":juggling_tone3:‍♀️": "🤒",
    ":juggling_tone3:‍♂️": "🤓",
    ":juggling_tone3:": "🤔",
    ":juggling_tone4:‍♀️": "🤕",
    ":juggling_tone4:‍♂️": "🤖",
    ":juggling_tone4:": "🤗",
    ":juggling_tone5:‍♀️": "🤘🏻",
    ":juggling_tone5:‍♂️": "🤘🏼",
    ":juggling_tone5:": "🤘🏽",
    ":juggling:‍♀️": "🤘🏾",
    ":juggling:‍♂️": "🤘🏿",
    ":juggling:": "🤘",
    ":fencer:": "🤙🏻",
    ":wrestlers_tone1:‍♀️": "🤙🏼",
    ":wrestlers_tone1:‍♂️": "🤙🏽",
    ":wrestlers_tone1:": "🤙🏾",
    ":wrestlers_tone2:‍♀️": "🤙🏿",
    ":wrestlers_tone2:‍♂️": "🤙",
    ":wrestlers_tone2:": "🤚🏻",
    ":wrestlers_tone3:‍♀️": "🤚🏼",
    ":wrestlers_tone3:‍♂️": "🤚🏽",
    ":wrestlers_tone3:": "🤚🏾",
    ":wrestlers_tone4:‍♀️": "🤚🏿",
    ":wrestlers_tone4:‍♂️": "🤚",
    ":wrestlers_tone4:": "🤛🏻",
    ":wrestlers_tone5:‍♀️": "🤛🏼",
    ":wrestlers_tone5:‍♂️": "🤛🏽",
    ":wrestlers_tone5:": "🤛🏾",
    ":wrestlers:‍♀️": "🤛🏿",
    ":wrestlers:‍♂️": "🤛",
    ":wrestlers:": "🤜🏻",
    ":water_polo_tone1:‍♀️": "🤜🏼",
    ":water_polo_tone1:‍♂️": "🤜🏽",
    ":water_polo_tone1:": "🤜🏾",
    ":water_polo_tone2:‍♀️": "🤜🏿",
    ":water_polo_tone2:‍♂️": "🤜",
    ":water_polo_tone2:": "🤝",
    ":water_polo_tone3:‍♀️": "🤞🏻",
    ":water_polo_tone3:‍♂️": "🤞🏼",
    ":water_polo_tone3:": "🤞🏽",
    ":water_polo_tone4:‍♀️": "🤞🏾",
    ":water_polo_tone4:‍♂️": "🤞🏿",
    ":water_polo_tone4:": "🤞",
    ":water_polo_tone5:‍♀️": "🤟🏻",
    ":water_polo_tone5:‍♂️": "🤟🏼",
    ":water_polo_tone5:": "🤟🏽",
    ":water_polo:‍♀️": "🤟🏾",
    ":water_polo:‍♂️": "🤟🏿",
    ":water_polo:": "🤟",
    ":handball_tone1:‍♀️": "🤠",
    ":handball_tone1:‍♂️": "🤡",
    ":handball_tone1:": "🤢",
    ":handball_tone2:‍♀️": "🤣",
    ":handball_tone2:‍♂️": "🤤",
    ":handball_tone2:": "🤥",
    ":handball_tone3:‍♀️": "🤦🏻‍♀️",
    ":handball_tone3:‍♂️": "🤦🏻‍♂️",
    ":handball_tone3:": "🤦🏻",
    ":handball_tone4:‍♀️": "🤦🏼‍♀️",
    ":handball_tone4:‍♂️": "🤦🏼‍♂️",
    ":handball_tone4:": "🤦🏼",
    ":handball_tone5:‍♀️": "🤦🏽‍♀️",
    ":handball_tone5:‍♂️": "🤦🏽‍♂️",
    ":handball_tone5:": "🤦🏽",
    ":handball:‍♀️": "🤦🏾‍♀️",
    ":handball:‍♂️": "🤦🏾‍♂️",
    ":handball:": "🤦🏾",
    ":wilted_rose:": "🤦🏿‍♀️",
    ":drum:": "🤦🏿‍♂️",
    ":champagne_glass:": "🤦🏿",
    ":tumbler_glass:": "🤦‍♀️",
    ":spoon:": "🤦‍♂️",
    ":goal:": "🤦",
    ":first_place:": "🤧",
    ":second_place:": "🤨",
    ":third_place:": "🤩",
    ":boxing_glove:": "🤪",
    ":martial_arts_uniform:": "🤫",
    ":croissant:": "🤬",
    ":avocado:": "🤭",
    ":cucumber:": "🤮",
    ":bacon:": "🤯",
    ":potato:": "🤰🏻",
    ":carrot:": "🤰🏼",
    ":french_bread:": "🤰🏽",
    ":salad:": "🤰🏾",
    ":shallow_pan_of_food:": "🤰🏿",
    ":stuffed_flatbread:": "🤰",
    ":egg:": "🤱🏻",
    ":milk:": "🤱🏼",
    ":peanuts:": "🤱🏽",
    ":kiwi:": "🤱🏾",
    ":pancakes:": "🤱🏿",
    ":crab:": "🤱",
    ":lion_face:": "🤲🏻",
    ":scorpion:": "🤲🏼",
    ":turkey:": "🤲🏽",
    ":unicorn:": "🤲🏾",
    ":eagle:": "🤲🏿",
    ":duck:": "🤲",
    ":bat:": "🤳🏻",
    ":shark:": "🤳🏼",
    ":owl:": "🤳🏽",
    ":fox:": "🤳🏾",
    ":butterfly:": "🤳🏿",
    ":deer:": "🤳",
    ":gorilla:": "🤴🏻",
    ":lizard:": "🤴🏼",
    ":rhino:": "🤴🏽",
    ":shrimp:": "🤴🏾",
    ":squid:": "🤴🏿",
    ":cheese:": "🤴",
    ":bangbang:": "🤵🏻‍♀️",
    ":interrobang:": "🤵🏻‍♂️",
    ":tm:": "🤵🏻",
    ":information_source:": "🤵🏼‍♀️",
    ":left_right_arrow:": "🤵🏼‍♂️",
    ":arrow_up_down:": "🤵🏼",
    ":arrow_upper_left:": "🤵🏽‍♀️",
    ":arrow_upper_right:": "🤵🏽‍♂️",
    ":arrow_lower_right:": "🤵🏽",
    ":arrow_lower_left:": "🤵🏾‍♀️",
    ":leftwards_arrow_with_hook:": "🤵🏾‍♂️",
    ":arrow_right_hook:": "🤵🏾",
    ":hash:": "🤵🏿‍♀️",
    ":watch:": "🤵🏿‍♂️",
    ":hourglass:": "🤵🏿",
    ":keyboard:": "🤵‍♀️",
    ":eject:": "🤵‍♂️",
    ":fast_forward:": "🤵",
    ":rewind:": "🤶🏻",
    ":arrow_double_up:": "🤶🏼",
    ":arrow_double_down:": "🤶🏽",
    ":track_next:": "🤶🏾",
    ":track_previous:": "🤶🏿",
    ":play_pause:": "🤶",
    ":alarm_clock:": "🤷🏻‍♀️",
    ":stopwatch:": "🤷🏻‍♂️",
    ":timer:": "🤷🏻",
    ":hourglass_flowing_sand:": "🤷🏼‍♀️",
    ":pause_button:": "🤷🏼‍♂️",
    ":stop_button:": "🤷🏼",
    ":record_button:": "🤷🏽‍♀️",
    ":m:": "🤷🏽‍♂️",
    ":black_small_square:": "🤷🏽",
    ":white_small_square:": "🤷🏾‍♀️",
    ":arrow_forward:": "🤷🏾‍♂️",
    ":arrow_backward:": "🤷🏾",
    ":white_medium_square:": "🤷🏿‍♀️",
    ":black_medium_square:": "🤷🏿‍♂️",
    ":white_medium_small_square:": "🤷🏿",
    ":black_medium_small_square:": "🤷‍♀️",
    ":sunny:": "🤷‍♂️",
    ":cloud:": "🤷",
    ":umbrella2:": "🤸🏻‍♀️",
    ":snowman2:": "🤸🏻‍♂️",
    ":comet:": "🤸🏻",
    ":telephone:": "🤸🏼‍♀️",
    ":ballot_box_with_check:": "🤸🏼‍♂️",
    ":umbrella:": "🤸🏼",
    ":coffee:": "🤸🏽‍♀️",
    ":shamrock:": "🤸🏽‍♂️",
    ":point_up_tone1:": "🤸🏽",
    ":point_up_tone2:": "🤸🏾‍♀️",
    ":point_up_tone3:": "🤸🏾‍♂️",
    ":point_up_tone4:": "🤸🏾",
    ":point_up_tone5:": "🤸🏿‍♀️",
    ":point_up:": "🤸🏿‍♂️",
    ":skull_crossbones:": "🤸🏿",
    ":radioactive:": "🤸‍♀️",
    ":biohazard:": "🤸‍♂️",
    ":orthodox_cross:": "🤸",
    ":star_and_crescent:": "🤹🏻‍♀️",
    ":peace:": "🤹🏻‍♂️",
    ":yin_yang:": "🤹🏻",
    ":wheel_of_dharma:": "🤹🏼‍♀️",
    ":frowning2:": "🤹🏼‍♂️",
    ":relaxed:": "🤹🏼",
    "♀": "🤹🏽‍♀️",
    "♂": "🤹🏽‍♂️",
    ":aries:": "🤹🏽",
    ":taurus:": "🤹🏾‍♀️",
    ":gemini:": "🤹🏾‍♂️",
    ":cancer:": "🤹🏾",
    ":leo:": "🤹🏿‍♀️",
    ":virgo:": "🤹🏿‍♂️",
    ":libra:": "🤹🏿",
    ":scorpius:": "🤹‍♀️",
    ":sagittarius:": "🤹‍♂️",
    ":capricorn:": "🤹",
    ":aquarius:": "🤺",
    ":pisces:": "🤼‍♀️",
    ":spades:": "🤼‍♂️",
    ":clubs:": "🤼",
    ":hearts:": "🤽🏻‍♀️",
    ":diamonds:": "🤽🏻‍♂️",
    ":hotsprings:": "🤽🏻",
    ":recycle:": "🤽🏼‍♀️",
    ":wheelchair:": "🤽🏼‍♂️",
    ":hammer_pick:": "🤽🏼",
    ":anchor:": "🤽🏽‍♀️",
    ":crossed_swords:": "🤽🏽‍♂️",
    "⚕": "🤽🏽",
    ":scales:": "🤽🏾‍♀️",
    ":alembic:": "🤽🏾‍♂️",
    ":gear:": "🤽🏾",
    ":atom:": "🤽🏿‍♀️",
    ":fleur-de-lis:": "🤽🏿‍♂️",
    ":warning:": "🤽🏿",
    ":zap:": "🤽‍♀️",
    ":white_circle:": "🤽‍♂️",
    ":black_circle:": "🤽",
    ":coffin:": "🤾🏻‍♀️",
    ":urn:": "🤾🏻‍♂️",
    ":soccer:": "🤾🏻",
    ":baseball:": "🤾🏼‍♀️",
    ":snowman:": "🤾🏼‍♂️",
    ":partly_sunny:": "🤾🏼",
    ":thunder_cloud_rain:": "🤾🏽‍♀️",
    ":ophiuchus:": "🤾🏽‍♂️",
    ":pick:": "🤾🏽",
    ":helmet_with_cross:": "🤾🏾‍♀️",
    ":chains:": "🤾🏾‍♂️",
    ":no_entry:": "🤾🏾",
    ":shinto_shrine:": "🤾🏿‍♀️",
    ":church:": "🤾🏿‍♂️",
    ":mountain:": "🤾🏿",
    ":beach_umbrella:": "🤾‍♀️",
    ":fountain:": "🤾‍♂️",
    ":golf:": "🤾",
    ":ferry:": "🤿",
    ":sailboat:": "🥀",
    ":skier::tone1:": "🥁",
    ":skier::tone2:": "🥂",
    ":skier::tone3:": "🥃",
    ":skier::tone4:": "🥄",
    ":skier::tone5:": "🥅",
    ":skier:": "🥇",
    ":ice_skate:": "🥈",
    ":basketball_player_tone1:‍♀️": "🥉",
    ":basketball_player_tone1:‍♂️": "🥊",
    ":basketball_player_tone1:": "🥋",
    ":basketball_player_tone2:‍♀️": "🥌",
    ":basketball_player_tone2:‍♂️": "🥍",
    ":basketball_player_tone2:": "🥎",
    ":basketball_player_tone3:‍♀️": "🥏",
    ":basketball_player_tone3:‍♂️": "🥐",
    ":basketball_player_tone3:": "🥑",
    ":basketball_player_tone4:‍♀️": "🥒",
    ":basketball_player_tone4:‍♂️": "🥓",
    ":basketball_player_tone4:": "🥔",
    ":basketball_player_tone5:‍♀️": "🥕",
    ":basketball_player_tone5:‍♂️": "🥖",
    ":basketball_player_tone5:": "🥗",
    ":basketball_player:‍♀️": "🥘",
    ":basketball_player:‍♂️": "🥙",
    ":basketball_player:": "🥚",
    ":tent:": "🥛",
    ":fuelpump:": "🥜",
    ":scissors:": "🥝",
    ":white_check_mark:": "🥞",
    ":airplane:": "🥟",
    ":envelope:": "🥠",
    ":fist_tone1:": "🥡",
    ":fist_tone2:": "🥢",
    ":fist_tone3:": "🥣",
    ":fist_tone4:": "🥤",
    ":fist_tone5:": "🥥",
    ":fist:": "🥦",
    ":raised_hand_tone1:": "🥧",
    ":raised_hand_tone2:": "🥨",
    ":raised_hand_tone3:": "🥩",
    ":raised_hand_tone4:": "🥪",
    ":raised_hand_tone5:": "🥫",
    ":raised_hand:": "🥬",
    ":v_tone1:": "🥭",
    ":v_tone2:": "🥮",
    ":v_tone3:": "🥯",
    ":v_tone4:": "🥰",
    ":v_tone5:": "🥱",
    ":v:": "🥳",
    ":writing_hand_tone1:": "🥴",
    ":writing_hand_tone2:": "🥵",
    ":writing_hand_tone3:": "🥶",
    ":writing_hand_tone4:": "🥺",
    ":writing_hand_tone5:": "🥻",
    ":writing_hand:": "🥼",
    ":pencil2:": "🥽",
    ":black_nib:": "🥾",
    ":heavy_check_mark:": "🥿",
    ":heavy_multiplication_x:": "🦀",
    ":cross:": "🦁",
    ":star_of_david:": "🦂",
    ":sparkles:": "🦃",
    ":eight_spoked_asterisk:": "🦄",
    ":eight_pointed_black_star:": "🦅",
    ":snowflake:": "🦆",
    ":sparkle:": "🦇",
    ":x:": "🦈",
    ":negative_squared_cross_mark:": "🦉",
    ":question:": "🦊",
    ":grey_question:": "🦋",
    ":grey_exclamation:": "🦌",
    ":exclamation:": "🦍",
    ":heart_exclamation:": "🦎",
    ":heart:": "🦏",
    ":heavy_plus_sign:": "🦐",
    ":heavy_minus_sign:": "🦑",
    ":heavy_division_sign:": "🦒",
    ":arrow_right:": "🦓",
    ":curly_loop:": "🦔",
    ":loop:": "🦕",
    ":arrow_heading_up:": "🦖",
    ":arrow_heading_down:": "🦗",
    ":asterisk:": "🦘",
    ":arrow_left:": "🦙",
    ":arrow_up:": "🦚",
    ":arrow_down:": "🦛",
    ":black_large_square:": "🦜",
    ":white_large_square:": "🦝",
    ":star:": "🦞",
    ":o:": "🦟",
    ":zero:": "🦠",
    ":wavy_dash:": "🦡",
    ":part_alternation_mark:": "🦢",
    ":one:": "🦥",
    ":two:": "🦦",
    ":congratulations:": "🦧",
    ":secret:": "🦨",
    ":three:": "🦩",
    ":four:": "🦪",
    ":five:": "🦮",
    ":six:": "🦯",
    ":seven:": "🦰",
    ":eight:": "🦱",
    ":nine:": "🦲",
    ":copyright:": "🦳",
    ":registered:": "🦴",
    "": "🦵🏻",
}


def smoltext(text=False):
    if text:
        return text.translate(
            str.maketrans(
                {
                    "a": "ᵃ",
                    "b": "ᵇ",
                    "c": "ᶜ",
                    "d": "ᵈ",
                    "e": "ᵉ",
                    "f": "ᶠ",
                    "g": "ᵍ",
                    "h": "ʰ",
                    "i": "ᶦ",
                    "j": "ʲ",
                    "k": "ᵏ",
                    "l": "ˡ",
                    "m": "ᵐ",
                    "n": "ⁿ",
                    "o": "ᵒ",
                    "p": "ᵖ",
                    "q": "ᑫ",
                    "r": "ʳ",
                    "s": "ˢ",
                    "t": "ᵗ",
                    "u": "ᵘ",
                    "v": "ᵛ",
                    "w": "ʷ",
                    "x": "ˣ",
                    "y": "ʸ",
                    "z": "ᶻ",
                }
            )
        )
    return None


def smallcaps(text=False):
    if text:
        return text.translate(
            str.maketrans(
                {
                    "a": "ᴀ",
                    "b": "ʙ",
                    "c": "ᴄ",
                    "d": "ᴅ",
                    "e": "ᴇ",
                    "f": "ғ",
                    "g": "ɢ",
                    "h": "ʜ",
                    "i": "ɪ",
                    "j": "ᴊ",
                    "k": "ᴋ",
                    "l": "ʟ",
                    "m": "ᴍ",
                    "n": "ɴ",
                    "o": "ᴏ",
                    "p": "ᴘ",
                    "q": "ǫ",
                    "r": "ʀ",
                    "s": "s",
                    "t": "ᴛ",
                    "u": "ᴜ",
                    "v": "ᴠ",
                    "w": "ᴡ",
                    "x": "x",
                    "y": "ʏ",
                    "z": "ᴢ",
                }
            )
        )
    return None


def swapcasealpha(text=False):
    if text:
        return text.translate(
            str.maketrans(
                {
                    "a": "A",
                    "b": "B",
                    "c": "C",
                    "d": "D",
                    "e": "E",
                    "f": "F",
                    "g": "G",
                    "h": "H",
                    "i": "I",
                    "j": "J",
                    "k": "K",
                    "l": "L",
                    "m": "M",
                    "n": "N",
                    "o": "O",
                    "p": "P",
                    "q": "Q",
                    "r": "R",
                    "s": "S",
                    "t": "T",
                    "u": "U",
                    "v": "V",
                    "w": "W",
                    "x": "X",
                    "y": "Y",
                    "z": "Z",
                    "A": "a",
                    "B": "b",
                    "C": "c",
                    "D": "d",
                    "E": "e",
                    "F": "f",
                    "G": "g",
                    "H": "h",
                    "I": "i",
                    "J": "j",
                    "K": "k",
                    "L": "l",
                    "M": "m",
                    "N": "n",
                    "O": "o",
                    "P": "p",
                    "Q": "q",
                    "R": "r",
                    "S": "s",
                    "T": "t",
                    "U": "u",
                    "V": "v",
                    "W": "w",
                    "X": "x",
                    "Y": "y",
                    "Z": "z",
                }
            )
        )
    return None


ordinal = lambda n: "%d%s" % (
    n,
    "tsnrhtdd"[(math.floor(n / 10) % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
)


def convert_hex_to_ascii(h):
    chars_in_reverse = []
    while h != 0x0:
        chars_in_reverse.append(chr(h & 0xFF))
        h = h >> 8

    chars_in_reverse.reverse()
    return "".join(chars_in_reverse)


async def ocr_function(message, client, args):
    try:
        url = None
        if len(message.attachments):
            url = message.attachments[0].url
        elif len(message.embeds) and message.embeds[0].image.url != discord.Embed.Empty:
            url = message.embeds[0].image.url
        elif (
            len(message.embeds)
            and message.embeds[0].thumbnail.url != discord.Embed.Empty
        ):
            url = message.embeds[0].thumbnail.url
        elif len(args) and args[0]:
            url = args[0]
        else:
            lessage = (
                await message.channel.history(limit=1, before=message).flatten()
            )[0]
            if len(lessage.attachments):
                url = lessage.attachments[0].url
            elif (
                len(lessage.embeds)
                and lessage.embeds[0].image.url != discord.Embed.Empty
            ):
                url = lessage.embeds[0].image.url
            elif (
                len(lessage.embeds)
                and lessage.embeds[0].thumbnail.url != discord.Embed.Empty
            ):
                url = lessage.embeds[0].thumbnail.url
            elif len(args) and args[0]:
                url = args[0]
        logger.debug(url)
        try:
            input_image_blob = await netcode.simple_get_image(url)
        except Exception as e:
            await message.add_reaction("🚫")
            await messagefuncs.sendWrappedMessage(
                f"Could not retrieve image with url {url} ({e})",
                message.channel,
                delete_after=60,
            )
            return
        input_image_blob.seek(0)
        input_image = Image.open(input_image_blob)
        input_image_blob.seek(0)
        target_url = f'http://{config["ocr"]["host"]}:{config["ocr"]["port"]}/file'
        image_to_text = ujson.loads(
            await netcode.simple_post_image(
                target_url,
                input_image_blob,
                url.split("/")[-1],
                Image.MIME[input_image.format],
            )
        )["result"]
        output_message = f">>> {image_to_text}"
        if (
            len(args) == 3
            and type(args[1]) is discord.Member
            and args[1] == message.author
        ):
            await messagefuncs.sendWrappedMessage(output_message, message.channel)
        elif len(args) == 3 and type(args[1]) is discord.Member:
            await messagefuncs.sendWrappedMessage(output_message, args[1])
        else:
            await messagefuncs.sendWrappedMessage(output_message, message.channel)
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("OCR[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def mobilespoil_function(message, client, args):
    try:
        input_image_blob = io.BytesIO()
        if len(message.attachments):
            lessage = None
            await message.attachments[0].save(input_image_blob)
        else:
            lessage = (
                await message.channel.history(limit=1, before=message).flatten()
            )[0]
            if not len(lessage.attachments):
                return await messagefuncs.sendWrappedMessage(
                    "Could not find image to spoil for mobilespoilfunction in your last or current message.",
                    message.author,
                )
            await lessage.attachments[0].save(input_image_blob)
        if (
            len(args) != 3
            or type(args[1]) is not discord.Member
            or (
                type(message.channel) == discord.DMChannel
                and message.author.id == client.user.id
            )
        ):
            try:
                await message.delete()
                if lessage:
                    await lessage.delete()
            except discord.Forbidden as e:
                if type(message.channel) != discord.DMChannel:
                    logger.error(
                        "Forbidden to delete message in " + str(message.channel)
                    )
                pass
        if len(args) == 3 and type(args[1]) is discord.Member:
            channel = args[1]
            content = ""
        else:
            content = "\n" + (" ".join(args))
            channel = message.channel
        content = f"Spoilered for {message.author.display_name}{content}"
        input_image_blob.seek(0)
        output_message = await messagefuncs.sendWrappedMessage(
            content,
            channel,
            files=[
                discord.File(
                    input_image_blob, "SPOILER_" + message.attachments[0].filename
                )
            ],
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("MSF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def scramble_function(message, client, args):
    try:
        if len(message.attachments) == 0:
            if len(args) != 3 or type(args[1]) is not discord.Member:
                await messagefuncs.sendWrappedMessage(
                    "No image attached to scramble.", message.channel, delete_after=60
                )
            return
        input_image_blob = io.BytesIO()
        await message.attachments[0].save(input_image_blob)
        if (
            len(args) != 3
            or type(args[1]) is not discord.Member
            or (
                type(message.channel) == discord.DMChannel
                and message.author.id == client.user.id
            )
        ):
            try:
                await message.delete()
            except discord.Forbidden as e:
                if type(message.channel) != discord.DMChannel:
                    logger.error(
                        "Forbidden to delete message in " + str(message.channel)
                    )
                pass
        target = (
            args[1]
            if len(args) == 3 and type(args[1]) is discord.Member
            else message.channel
        )
        output_message = await messagefuncs.sendWrappedMessage(
            f"Scrambling image... ({input_image_blob.getbuffer().nbytes} bytes loaded)",
            target,
        )
        input_image_blob.seek(0)
        input_image = Image.open(input_image_blob)
        if input_image.size == (1, 1):
            raise ValueError("input image must contain more than 1 pixel")
        number_of_regions = 1  # number_of_colours(input_image)
        key_image = None
        region_lists = create_region_lists(input_image, key_image, number_of_regions)
        random.seed(input_image.size)
        logger.debug("Shuffling scramble blob")
        shuffle(region_lists)
        output_image = swap_pixels(input_image, region_lists)
        output_image_blob = io.BytesIO()
        logger.debug("Saving scramble blob")
        output_image.save(output_image_blob, format="PNG", optimize=True)
        output_image_blob.seek(0)
        await output_message.delete()
        output_message = await messagefuncs.sendWrappedMessage(
            f"Scrambled for {message.author.display_name}",
            output_message.channel,
            files=[discord.File(output_image_blob, message.attachments[0].filename)],
        )
        await output_message.add_reaction("🔎")
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("SIF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def number_of_colours(image):
    return len(set(list(image.getdata())))


def create_region_lists(input_image, key_image, number_of_regions):
    template = create_template(input_image, key_image, number_of_regions)
    number_of_regions_created = len(set(template))
    region_lists = [[] for i in range(number_of_regions_created)]
    for i in range(len(template)):
        region = template[i]
        region_lists[region].append(i)
    odd_region_lists = [
        region_list for region_list in region_lists if len(region_list) % 2
    ]
    for i in range(len(odd_region_lists) - 1):
        odd_region_lists[i].append(odd_region_lists[i + 1].pop())
    return region_lists


def create_template(input_image, key_image, number_of_regions):
    width, height = input_image.size
    return [0] * (width * height)


def no_small_pixel_regions(pixel_regions, number_of_regions_created):
    counts = [0 for i in range(number_of_regions_created)]
    for value in pixel_regions:
        counts[value] += 1
    if all(counts[i] >= 256 for i in range(number_of_regions_created)):
        return True


def shuffle(region_lists):
    for region_list in region_lists:
        length = len(region_list)
        for i in range(length):
            j = random.randrange(length)
            region_list[i], region_list[j] = region_list[j], region_list[i]


def measure(pixel):
    """Return a single value roughly measuring the brightness.

    Not intended as an accurate measure, simply uses primes to prevent two
    different colours from having the same measure, so that an image with
    different colours of similar brightness will still be divided into
    regions.
    """
    if type(pixel) is int:
        return pixel
    else:
        r, g, b = pixel[:3]
        return r * 2999 + g * 5869 + b * 1151


def swap_pixels(input_image, region_lists):
    pixels = list(input_image.getdata())
    for region in region_lists:
        for i in range(0, len(region) - 1, 2):
            pixels[region[i]], pixels[region[i + 1]] = (
                pixels[region[i + 1]],
                pixels[region[i]],
            )
    scrambled_image = Image.new(input_image.mode, input_image.size)
    scrambled_image.putdata(pixels)
    return scrambled_image


def memfrob(plain=""):
    plain = list(plain)
    xok = 0x2A
    length = len(plain)
    kek = []
    for x in range(0, length):
        kek.append(hex(ord(plain[x])))
    for x in range(0, length):
        kek[x] = hex(int(kek[x], 16) ^ int(hex(xok), 16))

    cipher = ""
    for x in range(0, length):
        cipher = cipher + convert_hex_to_ascii(int(kek[x], 16))
    return cipher


def rot32768(s):
    y = ""
    for x in s:
        y += chr(ord(x) ^ 0x8000)
    return y


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.utcnow()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ""

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(int(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(int(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(int(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(int(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(int(day_diff / 30)) + " months ago"
    return str(int(day_diff / 365)) + " years ago"


async def rot13_function(message, client, args):
    global config
    try:
        if len(args) == 3 and type(args[1]) in [discord.Member, discord.User]:
            if message.author.id == client.user.id:
                if message.content.startswith("Mod Report"):
                    return await messagefuncs.sendWrappedMessage(
                        codecs.encode(
                            message.content.split(
                                " via reaction to "
                                if " via reaction to " in message.content
                                else "\n",
                                1,
                            )[1],
                            "rot_13",
                        ),
                        args[1],
                    )
                else:
                    return await messagefuncs.sendWrappedMessage(
                        "Spoiler from conversation in <#{}>{} <https://discordapp.com/channels/{}/{}/{}>\n{}: {}".format(
                            message.channel.id,
                            f" ({message.channel.guild.name})"
                            if type(message.channel) is not discord.DMChannel
                            else "",
                            message.channel.guild.id,
                            message.channel.id,
                            message.id,
                            message.content.split(": ", 1)[0],
                            codecs.encode(message.content.split(": ", 1)[1], "rot_13"),
                        ),
                        args[1],
                    )
            elif not args[1].bot:
                return await messagefuncs.sendWrappedMessage(
                    "Spoiler from conversation in <#{}>{} <https://discordapp.com/channels/{}/{}/{}>\n{}: {}".format(
                        message.channel.id,
                        f" ({message.channel.guild.name})"
                        if type(message.channel) is not discord.DMChannel
                        else "",
                        message.channel.guild.id,
                        message.channel.id,
                        message.id,
                        message.author.display_name,
                        codecs.encode(message.content, "rot_13"),
                    ),
                    args[1],
                )
            else:
                return logger.debug("Ignoring bot trigger")
        elif len(args) == 2 and args[1] == "INTPROC":
            return codecs.encode(args[0], "rot_13")
        else:
            if (
                len(args) == 3
                and type(args[1]) in [discord.Member, discord.User]
                and args[1].bot
            ):
                return logger.debug("Ignoring bot reaction")
            elif (
                len(args) == 3
                and type(args[1]) in [discord.Member, discord.User]
                and not args[1].bot
            ):
                logger.debug(args[1])
            messageContent = f"**{message.author.display_name}**: {codecs.encode(' '.join(args), 'rot_13')}"
            botMessage = await messagefuncs.sendWrappedMessage(
                messageContent, message.channel
            )
            await botMessage.add_reaction(
                client.get_emoji(int(config["discord"]["rot13"]))
            )
            try:
                await message.delete()
            except discord.Forbidden as e:
                if type(message.channel) != discord.DMChannel:
                    logger.error(
                        "Forbidden to delete message in " + str(message.channel)
                    )
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("R13F[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def spoiler_function(message, client, args):
    try:
        rotate_function = memfrob
        if message.author.id == 429368441577930753:
            if len(message.clean_content.split(": ", 1)[1]) != len(
                message.clean_content.split(": ", 1)[1].encode()
            ):
                rotate_function = rot32768
        else:
            if len(message.clean_content) != len(message.clean_content.encode()):
                rotate_function = rot32768
        if len(args) == 3 and type(args[1]) is discord.Member:
            if message.author.id == 429368441577930753:
                if type(message.channel) == discord.DMChannel:
                    return await messagefuncs.sendWrappedMessage(
                        "Spoiler from DM {}**: {}".format(
                            message.clean_content.split("**: ", 1)[0],
                            rotate_function(
                                swapcasealpha(message.clean_content.split("**: ", 1)[1])
                            ).replace("\n", " "),
                        ),
                        args[1],
                    )
                else:
                    return await messagefuncs.sendWrappedMessage(
                        "Spoiler from conversation in <#{}> ({}) <https://discordapp.com/channels/{}/{}/{}>\n{}**: {}".format(
                            message.channel.id,
                            message.channel.guild.name,
                            message.channel.guild.id,
                            message.channel.id,
                            message.id,
                            message.clean_content.split("**: ", 1)[0],
                            rotate_function(
                                swapcasealpha(message.clean_content.split("**: ", 1)[1])
                            ).replace("\n", " "),
                        ),
                        args[1],
                    )
            else:
                logger.debug("MFF: Backing out, not my message.")
        else:
            content_parts = message.clean_content.split(" ", 1)
            if not len(content_parts) == 2:
                return await messagefuncs.sendWrappedMessage(
                    "No spoilertext provided", message.channel, delete_after=60
                )
            messageContent = (
                "**"
                + message.author.display_name
                + "**: "
                + swapcasealpha(rotate_function(content_parts[1].replace(" ", "\n")))
            )
            botMessage = await messagefuncs.sendWrappedMessage(
                messageContent, message.channel
            )
            await botMessage.add_reaction("🙈")
            try:
                await message.delete()
            except discord.Forbidden as e:
                if type(message.channel) != discord.DMChannel:
                    logger.error(f"Forbidden to delete message in {message.channel}")
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("MFF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def reaction_request_function(message, client, args):
    global config
    try:
        if not message.channel.permissions_for(message.author).external_emojis:
            return False
        flip = message.content.startswith("!tcaerx")
        emoji_query = args[0].strip(":")
        target = None
        try:
            urlParts = messagefuncs.extract_identifiers_messagelink.search(
                message.content
            ).groups()
            if len(urlParts) == 3:
                guild_id = int(urlParts[0])
                channel_id = int(urlParts[1])
                message_id = int(urlParts[2])
                guild = client.get_guild(guild_id)
                if guild is None:
                    logger.warning("QAF: Fletcher is not in guild ID " + str(guild_id))
                    return
                channel = guild.get_channel(channel_id)
                target = await channel.fetch_message(message_id)
        except AttributeError:
            pass
        if len(args) >= 2 and args[1].isnumeric() and int(args[1]) < 1000000:
            emoji = list(filter(lambda m: m.name == emoji_query, client.emojis))
            emoji = emoji[int(args[1])]
        else:
            if ":" in emoji_query:
                emoji_query = emoji_query.split(":")
                emoji_query[0] = messagefuncs.expand_guild_name(
                    emoji_query[0], suffix=""
                )
                filter_query = (
                    lambda m: m.name == emoji_query[1]
                    and m.guild.name == emoji_query[0]
                )
            else:
                filter_query = lambda m: m.name == emoji_query
                emoji = list(filter(filter_query, client.emojis))
                if len(emoji):
                    emoji = emoji.pop(0)
                else:
                    emoji_query = emoji_query[0]
                    try:
                        image_blob = await netcode.simple_get_image(
                            f"https://twemoji.maxcdn.com/v/13.0.0/72x72/{hex(ord(emoji_query))[2:]}.png"
                        )
                    except Exception as e:
                        logger.debug("404 Image Not Found")
                        await message.add_reaction("🚫")
                        return
                    image_blob.seek(0)
                    emoteServer = client.get_guild(
                        config.get(section="discord", key="emoteServer", default=0)
                    )
                    try:
                        emoji = await emoteServer.create_custom_emoji(
                            name=hex(ord(emoji_query))[2:],
                            image=image_blob.read(),
                            reason="xreact custom copier",
                        )
                    except discord.Forbidden:
                        logger.error("discord.emoteServer misconfigured!")
                    except discord.HTTPException:
                        image_blob.seek(0)
                        await random.choice(emoteServer.emojis).delete()
                        emoji = await emoteServer.create_custom_emoji(
                            name=hex(ord(emoji_query))[2:],
                            image=image_blob.read(),
                            reason="xreact custom copier",
                        )
        if len(args) >= 2 and args[-1].isnumeric() and int(args[1]) >= 1000000:
            target = await message.channel.fetch_message(int(args[-1]))
        if emoji:
            if target is None:
                async for historical_message in message.channel.history(
                    before=message, oldest_first=False
                ):
                    if historical_message.author != message.author:
                        target = historical_message
                        break
            if flip:
                image_blob = await netcode.simple_get_image(
                    f"https://cdn.discordapp.com/emojis/{emoji.id}.png?v=1"
                )
                image_blob.seek(0)
                image = Image.open(image_blob)
                flip_image = ImageOps.mirror(ImageOps.flip(image))
                output_image_blob = io.BytesIO()
                flip_image.save(output_image_blob, format="PNG", optimize=True)
                output_image_blob.seek(0)
                emoteServer = client.get_guild(
                    config.get(section="discord", key="emoteServer", default=0)
                )
                try:
                    processed_emoji = await emoteServer.create_custom_emoji(
                        name=emoji.name[::-1],
                        image=output_image_blob.read(),
                        reason="xreact flip-o-matic",
                    )
                except discord.Forbidden:
                    logger.error("discord.emoteServer misconfigured!")
                except discord.HTTPException:
                    output_image_blob.seek(0)
                    await random.choice(emoteServer.emojis).delete()
                    processed_emoji = await emoteServer.create_custom_emoji(
                        name=emoji.name[::-1],
                        image=output_image_blob.read(),
                        reason="xreact flip-o-matic",
                    )
                emoji = processed_emoji
            await target.add_reaction(emoji)
            await asyncio.sleep(1)
            try:
                await client.wait_for(
                    "raw_reaction_add",
                    timeout=6000.0,
                    check=lambda reaction: str(reaction.emoji) == str(emoji),
                )
            except asyncio.TimeoutError:
                pass
            try:
                await target.remove_reaction(emoji, client.user)
            except discord.NotFound:
                # Message deleted before we could remove the reaction
                pass
        try:
            if config["discord"].get("snappy"):
                await message.delete()
        except discord.Forbidden:
            logger.warning("XRF: Couldn't delete message but snappy mode is on")
            pass
    except IndexError as e:
        await message.add_reaction("🚫")
        await messagefuncs.sendWrappedMessage(
            f"XRF: Couldn't find reaction with name {emoji_query}, please check spelling or name {e}",
            message.author,
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("XRF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def blockquote_embed_function(message, client, args):
    try:
        title = None
        rollup = None
        if len(args) >= 1 and args[0][0:2] == "<<":
            limit = int(args[0][2:])
            title = " ".join(args[1:])
        elif len(args) >= 1:
            urlParts = messagefuncs.extract_identifiers_messagelink.search(
                message.content
            )
            if urlParts and len(urlParts.groups()) == 3:
                guild_id = int(urlParts.group(1))
                channel_id = int(urlParts.group(2))
                message_id = int(urlParts.group(3))
                guild = client.get_guild(guild_id)
                if guild is None:
                    logger.info("PMF: Fletcher is not in guild ID " + str(guild_id))
                    await message.add_reaction("🚫")
                    return await messagefuncs.sendWrappedMessage(
                        "I don't have permission to access that message, please check server configuration.",
                        message.author,
                    )
                channel = guild.get_channel(channel_id)
                target_message = await channel.fetch_message(message_id)
                # created_at is naîve, but specified as UTC by Discord API docs
                sent_at = target_message.created_at.strftime("%B %d, %Y %I:%M%p UTC")
                rollup = target_message.content
                if rollup == "":
                    rollup = "*No Text*"
                if (
                    message.guild
                    and message.guild.id == guild_id
                    and message.channel.id == channel_id
                ):
                    title = "Message from {} sent at {}".format(
                        target_message.author.name, sent_at
                    )
                elif message.guild and message.guild.id == guild_id:
                    title = "Message from {} sent in <#{}> at {}".format(
                        target_message.author.name, channel_id, sent_at
                    )
                else:
                    title = "Message from {} sent in #{} ({}) at {}".format(
                        target_message.author.name, channel.name, guild.name, sent_at
                    )
            limit = None
        else:
            limit = None
        if len(args) == 0 or (limit and limit <= 0):
            limit = 1
        if limit:
            historical_messages = []
            async for historical_message in message.channel.history(
                before=message, limit=None
            ):
                if historical_message.author == message.author:
                    historical_messages.append(historical_message)
                    limit -= 1
                if limit == 0:
                    break
            rollup = ""
            for message in historical_messages:
                rollup = f"{message.clean_content}\n{rollup}"
        else:
            if not rollup:
                if "\n" in message.content:
                    title = message.content.split("\n", 1)[0].split(" ", 1)[1]
                    rollup = message.content.split("\n", 1)[1]
                else:
                    rollup = message.content.split(" ", 1)[1]
        quoted_by = f"{message.author.name}#{message.author.discriminator}"
        if hasattr(message.author, "nick") and message.author.nick is not None:
            quoted_by = f"{message.author.nick} ({quoted_by})"
        else:
            quoted_by = f"On behalf of {quoted_by}"
        embed = discord.Embed().set_footer(
            icon_url=message.author.avatar_url, text=quoted_by
        )
        if title:
            embed.title = title
        if len(rollup) < 2048:
            embed.description = rollup
            rollup = None
        # 25 fields * 1024 characters
        # https://discordapp.com/developers/docs/resources/channel#embed-object-embed-field-structure
        elif len(rollup) <= 25 * 1024:
            msg_chunks = textwrap.wrap(rollup, 1024, replace_whitespace=False)
            for hunk in msg_chunks:
                embed.add_field(name="\u1160", value=hunk, inline=True)
            rollup = None
        else:
            # TODO send multiple embeds instead
            await messagefuncs.sendWrappedMessage(
                "Message too long, maximum quotable character count is 25 * 1024",
                message.author,
            )
        if not rollup:
            await messagefuncs.sendWrappedMessage(target=message.channel, embed=embed)
            try:
                if config["discord"].get("snappy"):
                    for message in historical_messages:
                        await message.delete()
                    await message.delete()
            except discord.Forbidden:
                logger.warning("BEF: Couldn't delete messages but snappy mode is on")
                pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("BEF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


async def zalgo_function(message, client, args):
    try:
        await messagefuncs.sendWrappedMessage(
            zalgo.zalgo(" ".join(args)), message.channel
        )
        try:
            if config["discord"].get("snappy"):
                await message.delete()
        except discord.Forbidden:
            logger.warning("ZF: Couldn't delete messages but snappy mode is on")
            pass
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("ZF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


# Thanks to Celer for this~!
ordinal = lambda n: str(n) + (
    "th"
    if (n % 10 > 3 or 10 < n % 100 < 20)
    else {0: "th", 1: "st", 2: "nd", 3: "rd"}[n % 10]
)


def fiche_function(content, message_id):
    try:
        if len(content) > int(config["pastebin"]["max_size"]):
            raise Exception(
                f'Exceeds max file size in pastebin > max_size ({config["pastebin"]["max_size"]})'
            )
        link = config["pastebin"]["base_url"]
        uuid = shortuuid.uuid(name=link + "/" + str(message_id))
        link += f"/{uuid}.txt"
        with open(f'{config["pastebin"]["base_path"]}/{uuid}.txt', "w") as output:
            output.write(content)
        return link
    except Exception as e:
        exc_type, exc_obj, exc_tb = exc_info()
        logger.error("FF[{}]: {} {}".format(exc_tb.tb_lineno, type(e).__name__, e))


def autoload(ch):
    ch.add_command(
        {
            "trigger": [
                "!rot13",
                "🕜",
                "<:rot13:539568301861371905>",
                "<:rot13:527988322879012894>",
            ],
            "function": rot13_function,
            "async": True,
            "args_num": 0,
            "args_name": ["message"],
            "description": "Replaces the message with a [ROT13](https://en.wikipedia.org/wiki/ROT13) version. React with <:rot13:539568301861371905> or 🕜 to receive a DM with the original message.",
            "syntax": "!rot13 message",
        }
    )

    ch.add_command(
        {
            "trigger": ["!spoiler", "🙈", "!memfrob", "🕦"],
            "function": spoiler_function,
            "async": True,
            "args_num": 0,
            "args_name": ["message"],
            "description": "Similar functionality to `!rot13`, but obfuscates the message more thoroughly and works with all characters (not just alphabetic ones). React with 🙈 to receive a DM with the original message.",
            "syntax": "!spoiler message",
        }
    )

    ch.add_command(
        {
            "trigger": ["!scramble", "🔎", "🔞"],
            "function": scramble_function,
            "async": True,
            "args_num": 0,
            "args_name": ["Image attachment"],
            "description": "Replaces image with a deep fried version. React with 🔎 to receive a DM with the original image.",
            "syntax": "!scramble` as a comment on an uploaded image`",
        }
    )

    ch.add_command(
        {
            "trigger": ["!mobilespoil", "\u1F4F3"],
            "function": mobilespoil_function,
            "async": True,
            "args_num": 0,
            "args_name": ["Image attachment"],
            "description": "Replaces image with a Discord spoilered version.",
            "syntax": "!mobilespoil` as a comment on an uploaded image`",
        }
    )

    ch.add_command(
        {
            "trigger": ["!md5"],
            "function": lambda message, client, args: hashlib.md5(
                " ".join(args).encode("utf-8")
            ).hexdigest(),
            "async": False,
            "args_num": 1,
            "args_name": [],
            "description": "Provides an [MD5](https://en.wikipedia.org/wiki/MD5) hash of the message text (does not work on images).",
            "syntax": "!md5 message",
        }
    )

    ch.add_command(
        {
            "trigger": ["!blockquote"],
            "function": blockquote_embed_function,
            "async": True,
            "args_num": 0,
            "args_name": [],
            "description": "Blockquote message(s) as a webhook embed (see syntax for details).",
            "syntax": "####Quote previous message\n**Syntax:** `!blockquote`\n\nCreates a blockquote of your previous message using a webhook embed. Webhooks have a higher character limit than messages, so this allows multiple messages to be combined into one.\n\n####Quote multiple previous messages\n**Syntax:** `!blockquote <<n (title)`\n\n**Example:** `!blockquote <<3 Hamlet's Soliloquy`\n\nCreates a blockquote from your past *n* messages, with optional title. The example would produce a quote from your past 3 messages, titled \"Hamlet's Soliloquy\".\n\n####Quote from message text\n**Syntax:** `!blockquote message`\n\n####Quote from message links\n**Syntax:** `!blockquote messagelink1 (messagelink2) (...)`\n\nCreates a blockquote from one or more linked messages.",
        }
    )

    ch.add_command(
        {
            "trigger": ["!smallcaps"],
            "function": lambda message, client, args: smallcaps(" ".join(args).lower()),
            "async": False,
            "args_num": 1,
            "args_name": [],
            "description": "Smallcaps text",
        }
    )

    ch.add_command(
        {
            "trigger": ["!smoltext"],
            "function": lambda message, client, args: smoltext(" ".join(args).lower()),
            "async": False,
            "args_num": 1,
            "args_name": [],
            "description": "Smol text (superscript)",
        }
    )

    ch.add_command(
        {
            "trigger": ["!zalgo"],
            "function": zalgo_function,
            "async": True,
            "args_num": 1,
            "args_name": [],
            "description": "HE COMES",
        }
    )

    ch.add_command(
        {
            "trigger": ["!xreact", "!tcaerx"],
            "function": reaction_request_function,
            "async": True,
            "args_num": 1,
            "args_name": ["Reaction name", "offset if ambiguous (optional)"],
            "description": "Request reaction (x-server)",
        }
    )

    ch.add_command(
        {
            "trigger": ["!ocr", "\U0001F50F"],
            "function": ocr_function,
            "long_run": "author",
            "async": True,
            "args_num": 0,
            "args_name": ["Image to be OCRed"],
            "description": "OCR",
        }
    )


async def autounload(ch):
    pass
