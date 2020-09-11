from arelle.ModelManager import ModelManager
from arelle.XhtmlValidate import xhtmlValidate
import sys, os, gettext
from arelle import CntlrWinMain, CntlrCmdLine, ModelObject
from arelle.ModelObjectFactory import parser
import tempfile
import bs4

import re
from lxml import etree
import random
import string

friendly_description_table = {
    "html:syntaxError": "HTML syntax error: input file does not follow the xHTML DTD",
    "EFM.5.02.05.anchorElementPosition": "Anchor located outside of root elements"
}


class Entry:
    message = ""
    code = ""
    friendly_desc = ""
    sourceLine = 0
    prevLine = ''
    sourceStr = ''
    nextLine = ''
    wasSubsequent = False
    ref_props = {}

    def __init__(self, msg, code, was_subsequent=False):
        global friendly_description_table
        self.message = msg
        self.code = code
        if code in friendly_description_table:
            self.friendly_desc = friendly_description_table[code]
        self.ref_props = {}
        self.wasSubsequent = was_subsequent

    def describe_offender(self):
        vals = '; '.join([f'{a}={b}' for a, b in self.ref_props.items() if a != 'QName'])
        return f'Offending element(s): {self.ref_props["QName"]}; {vals}'

    def __str__(self):
        return f':{self.sourceLine} - {self.message}'


def get_random_string(length):
    # Random string with the combination of lower and upper case
    letters = string.ascii_letters
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


import html


def format_report_html(entries):
    style_text = '''
        .entry {
            margin-bottom: 1.5em;
        }
        .subsequent {
            margin-top: -1.25em !important;
        }
        
        .arelle-message {
            font-size: 10pt;
            margin-left: 0.5em;
        }
        h3 {
            margin: 0;
        }


        .message {

        }

        .source {
            margin-left: 1em;
            font-family: monospace;
        }

        .lineno {
            min-width: 3.5em;
            text-align: right;
            margin-right: 0.5em;
            display: inline-block;
        }
        .grayed {
            color: gray;
        }
        .dark {
            color: #900;
        }
    '''
    htmls = f'<html><head><title>xHTML Validation Report</title><style>{style_text}</style></head><body>'
    for entry in entries:
        s = entry.sourceStr
        s = html.escape(s)
        if entry.wasSubsequent:
            htmls = htmls + f"<div class='entry subsequent'>" \
                            f"<div class='source'>{entry.describe_offender()}</div>" \
                            f"<div class='source'>" \
                            f"<div class='grayed'><span class='lineno'>{entry.sourceLine - 1}: </span>{html.escape(entry.prevLine)}</div>" \
                            f"<div class='dark'><span class='lineno'>{entry.sourceLine}: </span>{s}</div>" \
                            f"<div class='grayed'><span class='lineno'>{entry.sourceLine + 1}: </span>{html.escape(entry.nextLine)}</div>" \
                            f"</div>\n" \
                            f"</div>\n"
        else:
            htmls = htmls + f"<div class='entry'>" \
                            f"<div class='message'><h3>{entry.code}</h3>{entry.friendly_desc}</div>" \
                            f"<div class='arelle-message'>{entry.message}</div>" \
                            f"<div class='source'>{entry.describe_offender()}</div>" \
                            f"<div class='source'>" \
                            f"<div class='grayed'><span class='lineno'>{entry.sourceLine - 1}: </span>{html.escape(entry.prevLine)}</div>" \
                            f"<div class='dark'><span class='lineno'>{entry.sourceLine}: </span>{s}</div>" \
                            f"<div class='grayed'><span class='lineno'>{entry.sourceLine + 1}: </span>{html.escape(entry.nextLine)}</div>" \
                            f"</div>\n" \
                            f"</div>\n"
    htmls = htmls + "</body></html>"
    return htmls


def main(file, report_path):
    ignore_code_list = ['ix11.14.1.2:missingResources', 'ix11.12.1.2:missingReferences', 'arelle:ixdsTargetNotDefined',
                        'EFM.6.05.19', 'EFM.coverFacts', 'ix11.8.1.3:headerMissing', 'EFM.5.02.05.graphicFileError']
    fdin, temp_in_path = tempfile.mkstemp('.htm')
    fdout, temp_out_path = tempfile.mkstemp('.xml')
    # temp_in_path = get_random_string(16) + '.htm'
    # temp_out_path = get_random_string(16) + '.xml'
    with open(file, 'r', encoding='utf-8') as fso:
        with open(temp_in_path, 'w') as outFso:
            data = fso.read()
            nsStr = 'xmlns:dei="http://xbrl.sec.gov/dei/2018-01-31" xmlns:rr="http://xbrl.sec.gov/rr/2018-01-31" ' \
                    'xmlns:utr="http://www.xbrl.org/2009/utr" xmlns:link="http://www.xbrl.org/2003/linkbase" ' \
                    'xmlns:xbrli="http://www.xbrl.org/2003/instance" ' \
                    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink" ' \
                    'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" ' \
                    'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:num="http://www.xbrl.org/dtr/type/numeric" ' \
                    'xmlns:nonnum="http://www.xbrl.org/dtr/type/non-numeric" ' \
                    'xmlns:xbrldt="http://xbrl.org/2005/xbrldt" xmlns="http://www.w3.org/1999/xhtml" ' \
                    'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" ' \
                    'xmlns:ixt-sec="http://www.sec.gov/inlineXBRL/transformation/2015-08-31" ' \
                    'xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2015-02-26" ' \
                    'xmlns:pbf="http://www.pioneerinvestments.com/20200819" '
            data = re.sub(r'^<html[^>]*>', '<html %s>' % nsStr, data)
            outFso.write(data)

    gettext.install("arelle")
    args = [
        '-f',
        temp_in_path,
        '-v',
        '--efm',
        '--plugins',
        'validate/EFM',
        '--disclosureSystem',
        'efm-pragmatic-all-years',
        '--logFile',
        temp_out_path
    ]
    print('hello')
    CntlrCmdLine.parseAndRun(args)
    import logging
    logging.shutdown()
    print('bye')
    # print(temp_out_path)

    log_entries = []
    with open(temp_out_path, 'r') as fso:
        data = fso.read()
        soup = bs4.BeautifulSoup(data, 'xml')
        for entry in soup.find_all('entry'):
            if entry["level"] != 'warning' and entry['level'] != 'error':
                continue
            if entry['code'] in ignore_code_list:
                continue
            msg = entry.message.text
            was_first = True
            for ref in entry.find_all('ref'):
                if 'sourceLine' in ref.attrs:
                    logentry = Entry(msg, entry.attrs["code"], not was_first)
                    for prop in ref.find_all('property'):
                        logentry.ref_props[prop.attrs["name"]] = prop.attrs["value"]
                    logentry.sourceLine = int(ref.attrs['sourceLine'])
                    log_entries.append(logentry)
                    was_first = False
    with open(temp_in_path, 'r') as fso:
        lines = fso.readlines()
        lineno = 1
        entry_stack = [l for l in log_entries]

        for line in lines:
            line = line.strip()
            foundstack = None
            for idx, l in enumerate(entry_stack):
                if lineno == l.sourceLine - 1:
                    l.prevLine = line
                elif lineno == l.sourceLine + 1:
                    l.nextLine = line
                    foundstack = idx
                    break
                if lineno == l.sourceLine:
                    l.sourceStr = line
            if foundstack is not None:
                del entry_stack[foundstack]
            lineno += 1
    # for entry in log_entries:
    # print(entry)
    with open(report_path, 'w') as fso:
        fso.write(format_report_html(log_entries))
    os.close(fdin)
    os.close(fdout)
    os.remove(temp_out_path)
    os.remove(temp_in_path)
    # os.remove(temp_in_path)
    # os.remove(temp_out_path)
    # os.close(temp_in_path)
    # os.remove(temp_in_path)


main(sys.argv[1], sys.argv[2])
# print()
# print('\n'.join(sys.argv))
