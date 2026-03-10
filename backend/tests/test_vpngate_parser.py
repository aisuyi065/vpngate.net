from app.services.vpngate import decode_openvpn_config, merge_server_sources, parse_sites_html, parse_vpngate_csv

CSV_SAMPLE = """*vpn_servers\n#HostName,IP,Score,Ping,Speed,CountryLong,CountryShort,NumVpnSessions,Uptime,TotalUsers,TotalTraffic,LogType,Operator,Message,OpenVPN_ConfigData_Base64\npublic-vpn-1,1.2.3.4,100,10,2500000,Japan,JP,12,3600,345,999999,2weeks,Tester,Sample,ZmFrZS1jb25maWc=\n"""

HTML_SAMPLE = """
<table border='1' id='vg_hosts_table_id'>
<tr>
<td class='vg_table_header'><b>VPN 来源国家或地区</b></td>
<td class='vg_table_header'><b>目的 VPN 服务器</b></td>
<td class='vg_table_header'><b>VPN 会话数</b></td>
<td class='vg_table_header'><b>线路质量</b></td>
<td class='vg_table_header'><b>SSL-VPN</b></td>
<td class='vg_table_header'><b>L2TP/IPsec</b></td>
<td class='vg_table_header'><b>OpenVPN</b></td>
<td class='vg_table_header'><b>MS-SSTP</b></td>
<td class='vg_table_header'><b>操作员</b></td>
<td class='vg_table_header'><b>总分</b></td>
</tr>
<tr>
<td class='vg_table_row_1' style='text-align: center;'><img src='../images/flags/JP.png' width='32' height='32' /><br>Japan</td>
<td class='vg_table_row_1'><b><span style='font-size: 9pt;'>public-vpn-1</span></b><br><span style='font-size: 10pt;'>1.2.3.4</span></td>
<td class='vg_table_row_1' style='text-align: right;'>sessions</td>
<td class='vg_table_row_1' style='text-align: right;'>quality</td>
<td class='vg_table_row_1' style='text-align: center;'><a href='howto_softether.aspx'><img src='../images/yes_33.png' /><br><b>SSL-VPN</b></a><br>TCP: 443<BR>UDP: 支持</td>
<td class='vg_table_row_1' style='text-align: center;'><a href='howto_l2tp.aspx'><img src='../images/yes_33.png' /><br><b>L2TP/IPsec</b></a></td>
<td class='vg_table_row_1' style='text-align: center;'><a href='do_openvpn.aspx?fqdn=public-vpn-1&ip=1.2.3.4&tcp=443&udp=1194&sid=1&hid=2'><img src='../images/yes_33.png' /><br><b>OpenVPN</b></a><br>TCP: 443<BR>UDP: 1194</td>
<td class='vg_table_row_1' style='text-align: center; word-break: break-all; white-space: normal;'><a href='howto_sstp.aspx'><img src='../images/yes_33.png' /><br><b>MS-SSTP</b></a><p style='text-align: left'><span style='font-size: 8pt;'>SSTP 主机名 :<br /><b><span style='color: #006600;'>public-vpn-1</span></b></span></p></td>
<td class='vg_table_row_1'>operator</td>
<td class='vg_table_row_1'>100</td>
</tr>
</table>
"""


def test_parse_vpngate_csv_reads_openvpn_rows():
    servers = parse_vpngate_csv(CSV_SAMPLE)

    assert len(servers) == 1
    server = servers[0]
    assert server.hostname == "public-vpn-1"
    assert server.ip == "1.2.3.4"
    assert server.country_code == "JP"
    assert server.supports_openvpn is True
    assert server.openvpn_config_b64 == "ZmFrZS1jb25maWc="


def test_parse_sites_html_extracts_protocol_support_and_ports():
    details = parse_sites_html(HTML_SAMPLE)

    assert len(details) == 1
    detail = details[0]
    assert detail.ip == "1.2.3.4"
    assert detail.supports_softether is True
    assert detail.supports_l2tp is True
    assert detail.supports_openvpn is True
    assert detail.supports_sstp is True
    assert detail.openvpn_tcp_port == 443
    assert detail.openvpn_udp_port == 1194


def test_merge_server_sources_keeps_csv_payload_and_html_protocol_metadata():
    merged = merge_server_sources(parse_vpngate_csv(CSV_SAMPLE), parse_sites_html(HTML_SAMPLE))

    assert len(merged) == 1
    server = merged[0]
    assert server.supports_softether is True
    assert server.supports_l2tp is True
    assert server.supports_sstp is True
    assert server.openvpn_tcp_port == 443
    assert server.openvpn_udp_port == 1194
    assert server.openvpn_config_b64 == "ZmFrZS1jb25maWc="


def test_decode_openvpn_config_adds_legacy_cipher_fallback():
    server = parse_vpngate_csv(CSV_SAMPLE)[0]

    config = decode_openvpn_config(server)

    assert "data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:AES-128-CBC" in config
    assert "data-ciphers-fallback AES-128-CBC" in config
