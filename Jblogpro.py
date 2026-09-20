#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奕豪WebBuilder v-3.06.1033 - 网站生成器
作者:靳好宝 Email:uulov@qq.com (c)2026.09.20 Markdown转HTML发布
"""
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import os, sys, re, random, json, shutil, io
from datetime import datetime
from pypinyin import pinyin, Style
try:
    import chardet
except ImportError:
    chardet = None
try:
    import markdown as _md_lib
except ImportError:
    _md_lib = None

SUPPORTED_ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'utf-16', 'ascii']

def _detect_bom(raw):
    if raw[:3] == b'\xef\xbb\xbf':
        return 'utf-8-sig', raw[3:]
    elif raw[:2] == b'\xff\xfe':
        return 'utf-16-le', raw[2:]
    elif raw[:2] == b'\xfe\xff':
        return 'utf-16-be', raw[2:]
    return None, raw

def read_file(path, errors='replace'):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            raw = f.read()
    except (IOError, OSError) as e:
        if isinstance(e, PermissionError) and getattr(sys, 'frozen', False):
            return ''
        print(f'[WARN] 无法读取 {path}: {e}')
        return None
    bom_enc, data = _detect_bom(raw)
    if bom_enc:
        try:
            return data.decode(bom_enc, errors=errors)
        except Exception:
            pass
    if chardet:
        det = chardet.detect(raw)
        enc = det.get('encoding')
        if enc and enc.lower() != 'ascii':
            try:
                return raw.decode(enc, errors=errors)
            except Exception:
                pass
    for enc in SUPPORTED_ENCODINGS:
        try:
            return raw.decode(enc, errors=errors)
        except Exception:
            continue
    return raw.decode('utf-8', errors='replace')

def write_file(path, text, encoding='utf-8'):
    with open(path, 'w', encoding=encoding) as f:
        f.write(text)

def validate_compatibility(text, encoding='utf-8'):
    try:
        encoded = text.encode(encoding)
        decoded = encoded.decode(encoding)
        return decoded == text, encoding, len(encoded)
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        return False, encoding, 0, str(e)

def normalize_newlines(text):
    return text.replace('\r\n', '\n').replace('\r', '\n')

def is_temp_directory(path):
    """检测路径是否是临时目录"""
    if not path:
        return False
    path_lower = path.lower()
    temp_patterns = ['temp', 'tmp', 'onefile_', 'nuitka', 'pyinstaller', '~$']
    return any(p in path_lower for p in temp_patterns)

def get_program_dir():
    """获取程序所在目录（固定路径）"""
    # PyInstaller 设置 sys.frozen=True
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # Nuitka 编译后：sys.argv[0] 是 exe 路径（非临时目录），__file__ 指向临时目录
    argv0 = os.path.abspath(sys.argv[0])
    if argv0.endswith('.exe') and not is_temp_directory(os.path.dirname(argv0)):
        return os.path.dirname(argv0)
    # 开发态：用 __file__
    return os.path.dirname(os.path.abspath(__file__))

def get_work_dir():
    """智能获取工作目录（用户目录）"""
    cwd = os.getcwd()
    if not is_temp_directory(cwd):
        return cwd
    docs = os.path.expanduser('~')
    if os.path.exists(docs):
        return docs
    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    if os.path.exists(desktop):
        return desktop
    return os.path.expanduser('~')

PROGRAM_DIR = get_program_dir()
WORK_DIR = get_work_dir()

REQUIRED_DIRS = []
REQUIRED_FILES = {
    'domain.txt':'localhost\n','关键词.txt':'默认关键词\n',
    '栏目.txt':'默认栏目\n','整理.txt':'',
    '作者.txt':'靳好宝\n','分类.txt':'默认分类\n',
}
def ensure_dirs():
    for d in REQUIRED_DIRS:
        p = os.path.join(PROGRAM_DIR,d)
        if not os.path.exists(p): os.makedirs(p)
    for fn,ct in REQUIRED_FILES.items():
        p = os.path.join(PROGRAM_DIR,fn)
        if not os.path.exists(p):
            write_file(p, ct)

def c2p(text):
    result = []
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            py = pinyin(char, style=Style.TONE3, heteronym=False)
            if py and py[0]:
                result.append(py[0][0])
            else:
                result.append(char.lower())
        else:
            result.append(char)
    return ''.join(result)

def sfn(fn):
    return re.sub(r'[\\/:*?"<>|]','',fn)

def strip_html(text):
    text = '' if text is None else text
    return re.sub(r'<[^>]+>','',text).replace('&nbsp;','').replace('&nbsp','').strip()

def clean_title(title):
    """清除标题中的空格，保留数字（修复标题中数字被过滤的问题）"""
    return re.sub(r'\s+', '', title).strip()

def clean_filename(fn):
    """清除文件名中的空格和数字"""
    return re.sub(r'[\s\d]+','',fn)

def is_markdown_text(text):
    """检测文本是否为Markdown格式（非HTML）"""
    t = (text or '').strip()
    if not t:
        return False
    if re.search(r'<p\s*>|<div\s*>|<span\s*>|<br\s*/?>|<h[1-6]\s*>|<table', t, re.I):
        return False
    patterns = [
        r'^#{1,6}\s+\S',
        r'^>\s+\S',
        r'^\s*[-*+]\s+\S',
        r'^\s*\d+\.\s+\S',
        r'\[[^\]]{1,60}\]\((?:https?:)?//[^\s)]+\)',
        r'^\[[^\]]+\]:\s+https?://',
        r'```',
        r'`[^`\n]+`',
        r'^\s*[-*_]{3,}\s*$',
        r'!\[[^\]]*\]\((?:https?:)?//[^\s)]+\)',
    ]
    lines = t.split('\n')
    score = 0
    for p in patterns:
        if re.search(p, t, re.M):
            score += 1
    return score >= 2

def md_to_html(text, base_url='', strip_title=False):
    """Markdown转HTML。markdown库缺失时用内置简易转换。base_url用于相对路径图片补全域名。
    strip_title=True时去掉首个一级标题（避免与文章主标题重复显示）"""
    text = (text or '').strip()
    if not text:
        return ''
    lines = text.split('\n')
    for k, ln in enumerate(lines):
        if ln.strip():
            m = re.match(r'^#{1,6}\s*(.+)$', ln.strip())
            if m:
                lines[k] = m.group(1).strip()
            break
    text = '\n'.join(lines).strip()
    if not text:
        return ''
    if strip_title:
        lines_t = text.split('\n')
        idx = None
        for k, ln in enumerate(lines_t):
            if ln.strip():
                m = re.match(r'^#\s+(.+)$', ln.strip())
                if m:
                    idx = k
                break
        if idx is not None:
            lines_t[idx] = ''
        text = '\n'.join(lines_t).strip()
        if not text:
            return ''
    if _md_lib:
        try:
            html = _md_lib.markdown(
                text,
                extensions=['fenced_code', 'tables', 'sane_lists', 'toc'],
                output_format='html'
            )
            if base_url and re.search(r'<img[^>]+src="', html):
                def fix_img(m):
                    tag = m.group(0)
                    sm = re.search(r'src="([^"]*)"', tag)
                    if sm and not sm.group(1).startswith(('http', '//', 'data:')):
                        tag = tag.replace(sm.group(1), base_url + '/' + sm.group(1).lstrip('/'))
                    return tag
                html = re.sub(r'<img[^>]+src="[^"]*"[^>]*>', fix_img, html)
            return html.strip()
        except Exception:
            pass
    lines = normalize_newlines(text).split('\n')
    out = []
    i = 0
    in_list = False
    in_ol = False
    list_items = []
    ol_start = 1
    buf = []

    def flush_para():
        if buf:
            p = '\n'.join(buf).strip()
            if p:
                out.append(f'<p>&nbsp&nbsp{p}</p>')
            buf.clear()

    def flush_list():
        nonlocal in_list, in_ol
        if in_list:
            items = '\n'.join(f'<li>{it}</li>' for it in list_items if it)
            out.append(f'<ul>\n{items}\n</ul>')
            in_list = False
            list_items.clear()
        if in_ol:
            items = '\n'.join(f'<li>{it}</li>' for it in list_items if it)
            out.append(f'<ol start="{ol_start}">\n{items}\n</ol>')
            in_ol = False
            list_items.clear()

    while i < len(lines):
        s = lines[i].strip()
        if s.startswith('```'):
            flush_para()
            flush_list()
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i].rstrip())
                i += 1
            out.append('<pre><code>' + '\n'.join(code_lines) + '</code></pre>')
            i += 1
            continue
        if s.startswith('|') and '|' in s[1:]:
            flush_para()
            flush_list()
            tbl = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                tbl.append(lines[i].strip())
                i += 1
            if len(tbl) >= 2:
                cells = [c.strip() for c in tbl[0].strip('|').split('|')]
                head = ''.join(f'<th>{c}</th>' for c in cells)
                body_rows = []
                for row in tbl[1:]:
                    if re.match(r'^\s*\|[\s:|-]+\|?\s*$', row):
                        continue
                    cs = [c.strip() for c in row.strip('|').split('|')]
                    body_rows.append(''.join(f'<td>{c}</td>' for c in cs))
                out.append(f'<table>\n<tr>{head}</tr>\n' + '\n'.join(body_rows) + '\n</table>')
            continue
        if s.startswith('#'):
            m = re.match(r'^(#{1,6})\s*(.+)$', s)
            if m:
                flush_para()
                flush_list()
                lvl = min(len(m.group(1)), 6)
                txt = m.group(2).strip().replace('**', '')
                out.append(f'<h{lvl}>{txt}</h{lvl}>')
                i += 1
                continue
        if s.startswith('>'):
            flush_para()
            flush_list()
            q = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                q.append(lines[i].strip().lstrip('>').strip())
                i += 1
            out.append('<blockquote>\n' + '\n'.join(q) + '\n</blockquote>')
            continue
        m = re.match(r'^(\d+)\.\s+(.*)$', s)
        if m:
            flush_para()
            if in_list:
                flush_list()
            in_ol = True
            ol_start = int(m.group(1))
            list_items.append(m.group(2))
            i += 1
            continue
        m = re.match(r'^[-*+]\s+(.*)$', s)
        if m:
            flush_para()
            if in_ol:
                flush_list()
            in_list = True
            list_items.append(m.group(1))
            i += 1
            continue
        if s.startswith('---') or s.startswith('***') or s.startswith('___'):
            flush_para()
            flush_list()
            out.append('<hr>')
            i += 1
            continue
        if s == '':
            flush_para()
            flush_list()
            i += 1
            continue
        buf.append(s)
        i += 1
    flush_para()
    flush_list()
    result = '\n'.join(out)
    result = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', result)
    result = re.sub(r'__(.+?)__', r'<b>\1</b>', result)
    result = re.sub(r'(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)', r'<i>\1</i>', result)
    result = re.sub(r'(?<!_)_(?!_)([^_\n]+?)_(?!_)', r'<i>\1</i>', result)
    result = re.sub(r'~~(.+?)~~', r'<del>\1</del>', result)
    def link_sub(m):
        txt, url = m.group(1), m.group(2)
        return f'<a href="{url}" target="_blank">{txt}</a>'
    result = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link_sub, result)
    def img_sub(m):
        alt, src = m.group(1), m.group(2)
        if base_url and not src.startswith(('http', '//', 'data:')):
            src = base_url + '/' + src.lstrip('/')
        return f'<img src="{src}" alt="{alt}" hspace="5" vspace="5">'
    result = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', img_sub, result)
    return result.strip()

def get_first_words(text, min_len, max_len):
    clean = strip_html(text)
    chars = []
    for c in clean:
        if '\u4e00' <= c <= '\u9fff':
            chars.append(c)
        elif c.isalpha():
            chars.append(c)
        elif c == ' ':
            chars.append(' ')
        elif c in '，。！？、；：""''（）《》〈〉「」『』【】[]{}()<>':
            chars.append(c)
    result = ''.join(chars).strip()
    cn_count = len([c for c in result if '\u4e00' <= c <= '\u9fff'])
    if cn_count >= min_len:
        count = 0; pos = 0
        for i, c in enumerate(result):
            if '\u4e00' <= c <= '\u9fff':
                count += 1
                if count >= max_len: pos = i+1; break
        if pos == 0: pos = len(result)
        return result[:pos] + ('...' if len(result) > pos else '')
    elif result:
        return result[:max_len] + ('...' if len(result) > max_len else '')
    return clean[:max_len] + ('...' if len(clean) > max_len else '')

def get_min_pubs(text, min_cn=300):
    clean = strip_html(text)
    cn = sum(1 for c in clean if '\u4e00' <= c <= '\u9fff')
    return cn >= min_cn

def get_img_size_rule(w, h):
    if w >= 600:
        return '600', str(round(h * 600 / w))
    return str(w), str(h)

def build_inline_img(url, iw, ih, alt=''):
    rw, rh = get_img_size_rule(iw, ih)
    alt = (alt or '').replace('"', "'").strip()
    return f'<img src="{url}"  width="{rw}" height="{rh}" align="middle" alt="{alt}" hspace="5" vspace="5">'

def get_max_txt_number_in_dir(txt_dir):
    """获取指定目录下txt文件名的最大数字"""
    if not os.path.exists(txt_dir): return 0
    mx = 0
    for f in os.listdir(txt_dir):
        if f.endswith('.txt'):
            ns = re.findall(r'_(\d+)\.txt$', f)
            if ns: mx = max(mx, int(ns[-1]))
    return mx

class LogPanel:
    _instance = None
    def __init__(self):
        self.panel = None
    @classmethod
    def set_panel(cls, panel):
        cls._instance = panel
    @classmethod
    def add(cls, icon, msg, level='info'):
        if cls._instance and hasattr(cls._instance, 'log_t'):
            cls._instance._add_log(icon, msg, level)

class Msg:
    @staticmethod
    def info(t,m):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅{m}")
        LogPanel.add('✅',f'{t}: {m}', 'success')
    @staticmethod
    def warn(t,m):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️{m}")
        LogPanel.add('ℹ️',f'{t}: {m}', 'info')
    @staticmethod
    def error(t,m):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌{m}")
        LogPanel.add('❌',f'{t}: {m}', 'error')

class App:
    # 硬编码颜色配置
    DEFAULT_BG_COLOR = '#E6E6FA'
    DEFAULT_TOOLBAR_BG = '#9400D3'
    DEFAULT_BUTTON_BG = '#9ACD32'
    DEFAULT_BUTTON_FG = '#000000'
    DEFAULT_TEXT_COLOR = '#000000'
    DEFAULT_FONT_FAMILY = '宋体'
    DEFAULT_FONT_SIZE = 18
    DEFAULT_FONT_WEIGHT = 'normal'
    DEFAULT_FONT_SLANT = 'roman'

    def __init__(self,root):
        self.root=root
        self.topmost=False; self.published=False
        self.ustack=[]; self.rstack=[]; self.maxu=3; self.cur=None
        self.log_entries=[]
        self.last_access_path = PROGRAM_DIR
        self.root.title("奕豪WebBuilder v-3.05.1033  Email:uulov@qq.com (c)2026.09.20 Markdown转HTML发布")
        self.root.geometry("1200x850"); self.root.configure(bg='#E6E6FA')
        self._ui(); self._bind(); self._load()
        self._apply(); self.root.protocol("WM_DELETE_WINDOW",self._quit)
    def _ui(self):
        mb=tk.Menu(self.root); self.root.config(menu=mb)
        fm=tk.Menu(mb,tearoff=0)
        for l,c,a in [("新建(N)",self._new,"Ctrl+N"),("打开(O)",self._open,"Ctrl+O"),
                      (None,None,None),("保存(S)",self._save,"Ctrl+S"),
                      ("另存为(A)",self._sav2,"Ctrl+Shift+S"),(None,None,None),
                      ("设置",self._setd,None),(None,None,None),("退出",self._quit,None)]:
            if l is None: fm.add_separator()
            else: fm.add_command(label=l,command=c,accelerator=a)
        mb.add_cascade(label="文件",menu=fm)
        em=tk.Menu(mb,tearoff=0)
        for l,c,a in [("撤销",self._undo,"Ctrl+Z"),("重做",self._redo,"Ctrl+Y"),
                      (None,None,None),("剪切",self._cut,"Ctrl+X"),
                      ("复制",self._copy,"Ctrl+C"),("粘贴",self._paste,"Ctrl+V"),
                      (None,None,None),("全选",self._sel,"Ctrl+A")]:
            if l is None: em.add_separator()
            else: em.add_command(label=l,command=c,accelerator=a)
        mb.add_cascade(label="编辑",menu=em)
        self.tb=tk.Frame(self.root,bg='#9400D3',
                         highlightbackground='#9400D3',highlightthickness=2)
        self.tb.pack(side=tk.TOP,fill=tk.X)
        self._r1(); self._r2(); self._r3()
        ef=tk.Frame(self.root,bg='#E6E6FA')
        ef.pack(fill=tk.BOTH,expand=True,padx=5,pady=(5,2))
        tf=tk.Frame(ef,bg='white',bd=2,relief=tk.SUNKEN)
        tf.pack(fill=tk.BOTH,expand=True)
        self.t=tk.Text(tf,wrap=tk.WORD,font=('宋体',18),bg='white',fg='black',
                      padx=10,pady=10,insertwidth=2,selectbackground='#B0C4DE')
        self.t.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        sb=tk.Scrollbar(tf,command=self.t.yview); sb.pack(side=tk.RIGHT,fill=tk.Y)
        self.t.config(yscrollcommand=sb.set)
        self.t.bind('<<Modified>>',self._mod)
        ctx=tk.Menu(self.t,tearoff=0)
        for l,c in [("剪切",self._cut),("复制",self._copy),("粘贴",self._paste),
                    (None,None),("保存",self._save),("另存为",self._sav2),
                    (None,None),("新建",self._new),("打开",self._open),
                    (None,None),("设置",self._setd)]:
            if l is None: ctx.add_separator()
            else: ctx.add_command(label=l,command=c)
        self.t.bind('<Button-3>',lambda e:ctx.tk_popup(e.x_root,e.y_root))
        lf=tk.LabelFrame(self.root,text="操作日志",bg='#E6E6FA',fg='#000000',
                        font=('宋体',10,'bold'),padx=5,pady=3)
        lf.pack(fill=tk.X,padx=5,pady=(0,5))
        lff=tk.Frame(lf,bg='white')
        lff.pack(fill=tk.X,pady=2)
        tk.Button(lff,text="清空日志",command=self._clear_log,bg='#9ACD32',
                 width=8,font=('宋体',9)).pack(side=tk.LEFT,padx=3)
        tk.Button(lff,text="复制日志",command=self._copy_log,bg='#9ACD32',
                 width=8,font=('宋体',9)).pack(side=tk.LEFT,padx=3)
        tk.Label(lff,text="日志内容不保存，仅显示在界面和控制台",bg='#E6E6FA',
                fg='#666666',font=('宋体',8)).pack(side=tk.LEFT,padx=10)
        self.log_tf=tk.Frame(lf,bg='white',bd=1,relief=tk.SOLID)
        self.log_tf.pack(fill=tk.BOTH,expand=True,pady=3)
        self.log_t=tk.Text(self.log_tf,wrap=tk.WORD,font=('宋体',9),bg='white',
                          fg='black',height=6)
        self.log_sb=tk.Scrollbar(self.log_tf,command=self.log_t.yview)
        self.log_t.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        self.log_sb.pack(side=tk.RIGHT,fill=tk.Y)
        self.log_t.config(yscrollcommand=self.log_sb.set)
    def _mkb(self,p,txt,tip,cmd,bg='#9ACD32',w=None):
        b=tk.Button(p,text=txt,command=cmd,bg=bg,bd=1,
                   highlightbackground='#9370D8',relief=tk.RAISED,
                   padx=3,pady=1,font=('宋体',9))
        if w: b.config(width=w)
        tw=[None]
        def ie(e):
            if tw[0]: return
            x,y=e.x_root+10,e.y_root+10
            tp=tk.Toplevel(b); tp.wm_overrideredirect(True)
            tp.wm_geometry(f"+{x}+{y}")
            tk.Label(tp,text=tip,background='#FFFFDD',foreground='#000000',
                    relief=tk.SOLID,borderwidth=1,font=('宋体',9)).pack()
            tw[0]=tp
        def le(e):
            if tw[0]: tw[0].destroy(); tw[0]=None
        b.bind('<Enter>',ie); b.bind('<Leave>',le)
        return b
    def _ins(self,t):
        try:
            if self.t.tag_ranges(tk.SEL):
                self.t.delete(tk.SEL_FIRST,tk.SEL_LAST)
            self.t.insert(tk.INSERT,t)
        except: self.t.insert(tk.INSERT,t)
        self.t.focus_set()
    def _wrp(self,l,r):
        try:
            if self.t.tag_ranges(tk.SEL):
                s=self.t.get(tk.SEL_FIRST,tk.SEL_LAST)
                self.t.delete(tk.SEL_FIRST,tk.SEL_LAST)
                self.t.insert(tk.INSERT,l+s+r)
            else: self.t.insert(tk.INSERT,l+r)
        except: self.t.insert(tk.INSERT,l+r)
        self.t.focus_set()
    def _savu(self):
        c=self.t.get('1.0','end-1c')
        if self.ustack and self.ustack[-1]==c: return
        if len(self.ustack)>=self.maxu: self.ustack.pop(0)
        self.ustack.append(c); self.rstack.clear()
    def _mod(self,e=None):
        if self.t.edit_modified(): self._savu(); self.t.edit_modified(False)
    def _r1(self):
        r=tk.Frame(self.tb,bg='#9400D3'); r.pack(fill=tk.X,padx=2,pady=1)
        btns=[
            ('^','置顶切换',self._tog,{'bg':'#9370D8'}),
            ('时间','插入当前时间',self._time,{}),
            ('>','插入2个空格',lambda:self._ins('  '),{}),
            ('整理','用整理.txt替换',self._org,{}),
            ('txt','另存为txt到栏目-txt文件夹',self._stxt,{'w':3}),
            ('()','插入()',lambda:self._wrp('(',')'),{}),
            ('[]','插入[]',lambda:self._wrp('[',']'),{}),
            ('{}','插入{}',lambda:self._wrp('{','}'),{}),
            ('/','插入/',lambda:self._ins('/'),{}),
            ('<p>','插入<p>&nbsp',lambda:self._ins('<p>&nbsp&nbsp'),{}),
            ('</p>','插入</p>',lambda:self._ins('</p>'),{}),
            ('<br>','插入<br>',lambda:self._ins('<br>'),{}),
            ('#','插入#',lambda:self._ins('#'),{}),
            ('%','插入%',lambda:self._ins('%'),{}),
            ('@','插入@',lambda:self._ins('@'),{}),
            ('*','插入*',lambda:self._ins('*'),{}),
            ('_','插入_',lambda:self._ins('_'),{}),
            (',','插入,',lambda:self._ins(','),{}),
            ("'", "插入'", lambda:self._ins("'"),{}),
            ('"', '插入"', lambda:self._ins('"'),{}),
            ('!','插入!',lambda:self._ins('!'),{}),
            ('.','插入.',lambda:self._ins('.'),{}),
            (':','插入:',lambda:self._ins(':'),{}),
            (';','插入;',lambda:self._ins(';'),{}),
            ('...','插入...',lambda:self._ins('...'),{}),
        ]
        for t,tip,cmd,ex in btns:
            b=self._mkb(r,t,tip,cmd,**ex); b.pack(side=tk.LEFT,padx=1,pady=1)
    def _tog(self):
        self.topmost=not self.topmost
        self.root.attributes('-topmost',self.topmost)
    def _time(self):
        self._ins(datetime.now().strftime('%Y.%m.%d %H:%M:%S'))
    def _org(self):
        f=os.path.join(PROGRAM_DIR,'整理.txt')
        if not os.path.exists(f): Msg.info("整理","整理.txt 不存在"); return
        try:
            ct = read_file(f)
            if not ct: Msg.info("整理","整理.txt为空"); return
            t=self.t.get('1.0','end-1c')
            for line in ct.split('\n'):
                line=line.strip()
                if not line: continue
                p=line.split(' ',1); old=p[0].strip(); new=p[1].strip() if len(p)>1 else ''
                if old:
                    if old.isalpha() and old.isascii():
                        t=re.sub(re.escape(old),new,t,flags=re.IGNORECASE)
                    else: t=t.replace(old,new)
            self.t.delete('1.0','end'); self.t.insert('1.0',t)
            Msg.info("整理","完成")
        except Exception as e: Msg.error("整理",str(e))
    def _stxt(self):
        """txt按钮 - 保存到栏目-txt文件夹，递增数字"""
        c=self.t.get('1.0','end-1c').strip()
        if not c: return
        cat = self.cv.get().strip()
        if not cat: return
        txt_dir_name = cat + '-txt'
        txt_dir = os.path.join(PROGRAM_DIR, txt_dir_name)
        if not os.path.exists(txt_dir):
            os.makedirs(txt_dir)
        title = self.tv.get().strip()
        if not title:
            fl = c.split('\n')[0].strip()
            title = sfn(fl) or '未命名'
        title = sfn(title) or '未命名'
        author = self.av.get().strip() or '未知'
        cat_val = self.cv.get().strip()
        category = self.cav.get().strip() or '未知'
        date_str = datetime.now().strftime('%Y.%m.%d')
        date_pattern = r'20\d{2}\.\d{2}\.\d{2}'
        # 新格式：标题_作者_栏目_分类_全局递增id_日期.txt
        new6_pat = r'^(.+)_([^_]+)_([^_]+)_([^_]+)_([0-9]+)_(' + date_pattern + r')\.txt$'
        # 旧格式：标题_作者_分类_全局递增id_日期.txt
        new5_pat = r'^(.+)_([^_]+)_([^_]+)_([0-9]+)_(' + date_pattern + r')\.txt$'
        # 更旧格式：标题_序号_日期.txt
        old_pat = r'^(.+)_([0-9]+)_(' + date_pattern + r')\.txt$'
        max_n = 0
        existing_titles = []
        for f in os.listdir(txt_dir):
            if not f.endswith('.txt'):
                continue
            m = re.match(new6_pat, f)
            if m:
                max_n = max(max_n, int(m.group(5)))
                existing_titles.append(m.group(1))
                continue
            m = re.match(new5_pat, f)
            if m:
                max_n = max(max_n, int(m.group(4)))
                existing_titles.append(m.group(1))
                continue
            m = re.match(old_pat, f)
            if m:
                max_n = max(max_n, int(m.group(2)))
                existing_titles.append(m.group(1))
                continue
            # 无法解析的文件名，取文件名第一段作为标题
            existing_titles.append(f[:-4].split('_')[0])
        fn = f'{title}_{author}_{cat_val}_{category}_{max_n+1}_{date_str}.txt'
        # 按标题去重：只检测文件名第一段的标题，标题重复则跳过保存
        for et in existing_titles:
            if sfn(et) == title:
                Msg.info("保存",f"标题「{title}」已存在，跳过保存: {fn}")
                return
        try:
            write_file(os.path.join(txt_dir,fn), c)
            Msg.info("保存",f"已保存: {fn}")
            self._last_txt_fn=os.path.join(txt_dir,fn)
        except: pass
    def _r2(self):
        r=tk.Frame(self.tb,bg='#9400D3'); r.pack(fill=tk.X,padx=2,pady=1)
        btns=[
            ('图片','插入图片转WebP',self._img,{}),
            ('网图','插入网络图片转WebP',self._wangtu,{}),
            ('在线图片','插入在线图片(保留URL)',self._onlineimg,{}),
            ('全复制','复制全部内容',self._cpa,{}),
            ('清除','清除内容',self._clr,{'bg':'#FFD700'}),
            ('链接','插入超链接',self._link,{}),
            ('撤消','撤销',self._undo,{}),
            ('重做','重做',self._redo,{}),
            ('复制','复制选中',self._cpy,{}),
            ('剪切','剪切选中',self._cut,{}),
            ('粘贴','粘贴',self._paste,{'bg':'#FF8C00'}),
            ('删行首','删除行首空格',self._dlp,{}),
            ('删空行','删除空行',self._deL,{}),
            ('删空格','删除行内空格',self._dis,{}),
            ('规范','添加<p></p>标签',self._fmt,{}),
            ('MD转HTML','Markdown转HTML',self._md2html,{}),
            ('字数','统计字数',self._wcnt,{}),
            ('导入','导入TXT',self._imp,{}),
            ('新建','新建文章',self._new,{'bg':'#FF8C00'}),
            ('TXT存','保存到栏目-txt文件夹',self._stxc,{}),
            ('规范行首','规范行首空格',self._fmt2,{}),
            ('整理','格式化+随机插入关键词/链接',self._orgf,{}),
            ('程序首页','生成程序目录index.html及分页',self._program_home,{'bg':'#FAEBD7'}),
        ]
        for t,tip,cmd,ex in btns:
            b=self._mkb(r,t,tip,cmd,**ex); b.pack(side=tk.LEFT,padx=1,pady=1)
        self.pb=self._mkb(r,'发布','发布HTML',self._pubbtn,bg='#FF8C00',w=6)
        self.hb=self._mkb(r,'首页','生成首页',self._home,w=6,bg='#FAEBD7')
        self.wb=self._mkb(r,'字数','统计字数并生成链接',self._wcnt,w=6,bg='#9ACD32')
        self.vb=self._mkb(r,'撤销发布','撤销最近一次发布',self._unpub,w=6,bg='#808080')
        self.pb.pack(side=tk.LEFT,padx=1,pady=1)
        self.hb.pack(side=tk.LEFT,padx=1,pady=1)
        self.wb.pack(side=tk.LEFT,padx=1,pady=1)
        self.vb.pack(side=tk.LEFT,padx=1,pady=1)
    def _wangtu(self):
        cat=self.cv.get().strip()
        if not cat:
            Msg.info("提示","请先选择栏目"); return
        try: cb=self.root.clipboard_get()
        except: cb=''
        d=tk.Toplevel(self.root); d.title("插入网络图片")
        d.geometry(f"+{self.root.winfo_x()+300}+{self.root.winfo_y()+300}")
        d.transient(self.root); d.grab_set()
        tk.Label(d,text="图片URL:",font=('宋体',10)).pack(padx=10,pady=(10,5))
        uv=tk.StringVar(value=cb if cb.startswith('http') else '')
        tk.Entry(d,textvariable=uv,width=50,font=('宋体',10)).pack(padx=10,pady=5)
        def paste_url():
            try: uv.set(self.root.clipboard_get())
            except: Msg.info("提示","剪贴板为空")
        tk.Button(d,text="粘贴",command=paste_url,bg='#FF8C00',width=6,font=('宋体',10)).pack(pady=5)
        def ok():
            url=uv.get().strip()
            if not url: d.destroy(); return
            import urllib.request as ur
            idir=os.path.join(PROGRAM_DIR,cat,'image')
            if not os.path.exists(idir): os.makedirs(idir)
            fn=url.split('/')[-1].split('?')[0] or 'web_image'
            name,ext=os.path.splitext(fn)
            if any('\u4e00'<=c<='\u9fff' for c in name): name=c2p(name)
            is_webp=ext.lower()=='.webp'
            tn=sfn(name)+'.webp'; tp=os.path.join(idir,tn)
            try:
                from PIL import Image
                data=ur.urlopen(url,timeout=15).read()
                img=Image.open(io.BytesIO(data))
                w,h=img.size
                if w>600:
                    img=img.resize((600,int(h*600/w)),Image.LANCZOS)
                if is_webp:
                    img.save(tp,'WEBP',quality=70)
                else:
                    img.save(tp,'WEBP',quality=70,method=6)
            except ImportError:
                data=ur.urlopen(url,timeout=15).read()
                with open(tp,'wb') as f: f.write(data)
            ct=self.t.get('1.0','end-1c')
            fl=ct.split('\n')[0].strip() if ct else ''
            rel=os.path.join(cat,'image',tn).replace('\\','/')
            try:
                from PIL import Image
                img=Image.open(tp)
                iw,ih=img.size
                if iw<600:
                    self._ins(f'<img src="{rel}" alt="{fl}" width="{iw}" height="{ih}">')
                else:
                    self._ins(f'<img src="{rel}" alt="{fl}" width="600" height="{ih*600//iw}">')
                Msg.info("网图","已处理插入")
            except:
                self._ins(f'<img src="{rel}" alt="{fl}">')
                Msg.info("网图","已处理插入")
            d.destroy()
        tk.Button(d,text="确定",command=ok,bg='#9ACD32',width=10,font=('宋体',10)).pack(pady=10)
    def _onlineimg(self):
        """插入在线图片 - 保留URL，不下载不转WebP，按原图尺寸规则生成<img>并插入光标处"""
        try: cb=self.root.clipboard_get()
        except: cb=''
        ct=self.t.get('1.0','end-1c')
        d=tk.Toplevel(self.root); d.title("插入在线图片")
        d.geometry(f"+{self.root.winfo_x()+300}+{self.root.winfo_y()+300}")
        d.transient(self.root); d.grab_set()
        tk.Label(d,text="图片地址:",font=('宋体',10)).pack(padx=10,pady=(10,5),anchor='w')
        uv=tk.StringVar(value=cb if cb.startswith('http') else '')
        row=tk.Frame(d); row.pack(padx=10,pady=5,fill=tk.X)
        ent=tk.Entry(row,textvariable=uv,width=50,font=('宋体',10)); ent.pack(side=tk.LEFT,fill=tk.X,expand=True)
        def paste_url():
            try: uv.set(self.root.clipboard_get())
            except: Msg.info("提示","剪贴板为空")
        tk.Button(row,text="粘贴",command=paste_url,bg='#FF8C00',width=6,font=('宋体',10)).pack(side=tk.LEFT,padx=(5,0))
        def ok():
            url=uv.get().strip()
            if not url: d.destroy(); return
            if not url.startswith('http'):
                Msg.info("提示","图片地址需以http/https开头")
                return
            alt=get_first_words(ct, 55, 65).replace('"',"'")
            try:
                import urllib.request as ur
                req=ur.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
                data=ur.urlopen(req,timeout=15).read(1024*1024)
                w=h=None
                try:
                    from PIL import Image
                    im=Image.open(io.BytesIO(data)); w,h=im.size
                except Exception:
                    pass
                if w and h:
                    img=build_inline_img(url, w, h, alt)
                else:
                    img=build_inline_img(url, 600, 600, alt)
                self._ins(img)
                Msg.info("在线图片","已插入")
            except Exception as e:
                img=build_inline_img(url, 600, 600, alt)
                self._ins(img)
                Msg.info("在线图片",f"读取尺寸失败，按默认600宽插入: {e}")
            d.destroy()
        tk.Button(d,text="确定",command=ok,bg='#9ACD32',width=10,font=('宋体',10)).pack(pady=10)
    def _img(self):
        cat=self.cv.get().strip()
        if not cat:
            Msg.info("提示","请先选择栏目"); return
        fp=filedialog.askopenfilename(title="选择图片",
            filetypes=[("图片","*.png *.jpg *.jpeg *.bmp *.gif *.webp"),("*","*.*")],
            initialdir=PROGRAM_DIR)
        if not fp: return
        idir=os.path.join(PROGRAM_DIR,cat,'image')
        if not os.path.exists(idir): os.makedirs(idir)
        fn=os.path.basename(fp); name,ext=os.path.splitext(fn)
        if any('\u4e00'<=c<='\u9fff' for c in name): name=c2p(name)
        is_webp=ext.lower()=='.webp'
        tn=sfn(name)+'.webp'; tp=os.path.join(idir,tn)
        try:
            try:
                from PIL import Image
                img=Image.open(fp)
                w,h=img.size
                if w>600:
                    img=img.resize((600,int(h*600/w)),Image.LANCZOS)
                if is_webp:
                    img.save(tp,'WEBP',quality=70)
                else:
                    img.save(tp,'WEBP',quality=70,method=6)
            except ImportError:
                shutil.copy2(fp,tp)
                from PIL import Image
                img=Image.open(tp)
            ct=self.t.get('1.0','end-1c')
            fl=ct.split('\n')[0].strip() if ct else ''
            rel=os.path.join(cat,'image',tn).replace('\\','/')
            try:
                from PIL import Image
                img=Image.open(tp)
                iw,ih=img.size
                if iw<600:
                    self._ins(f'<img src="{rel}" alt="{fl}" width="{iw}" height="{ih}">')
                else:
                    self._ins(f'<img src="{rel}" alt="{fl}" width="600" height="{ih*600//iw}">')
            except:
                self._ins(f'<img src="{rel}" alt="{fl}">')
            Msg.info("图片","已处理插入")
        except Exception as e: Msg.error("图片",str(e))
    def _cpa(self):
        c=self.t.get('1.0','end-1c')
        self.root.clipboard_clear(); self.root.clipboard_append(c)
        Msg.info("复制","已全部复制")
    def _clr(self):
        self.t.delete('1.0','end')
        LogPanel.add('✅','内容已清除')
    def _link(self):
        try: cb=self.root.clipboard_get()
        except: cb=''
        d=tk.Toplevel(self.root); d.title("插入链接")
        d.geometry(f"+{self.root.winfo_x()+300}+{self.root.winfo_y()+300}")
        d.transient(self.root); d.grab_set()
        tk.Label(d,text="网址:",font=('宋体',10)).pack(padx=10,pady=(10,5))
        uv=tk.StringVar(value=cb if cb.startswith('http') else '')
        tk.Entry(d,textvariable=uv,width=50,font=('宋体',10)).pack(padx=10,pady=5)
        def ok():
            url=uv.get().strip()
            if not url: d.destroy(); return
            ct=self.t.get('1.0','end-1c')
            fl=ct.split('\n')[0].strip() if ct else '文章'
            w=fl[:30]+('...' if len(fl)>30 else '')
            t=self.tv.get().strip() or w
            self._ins(f'<a href="{url}" target="_blank" title="{t}">{w}</a>')
            d.destroy()
        tk.Button(d,text="确定",command=ok,bg='#9ACD32',width=10,font=('宋体',10)).pack(pady=10)
    def _cpy(self):
        try:
            if self.t.tag_ranges(tk.SEL):
                s=self.t.get(tk.SEL_FIRST,tk.SEL_LAST)
                self.root.clipboard_clear(); self.root.clipboard_append(s)
        except: pass
    def _cut(self):
        try: self.t.event_generate('<<Cut>>')
        except: pass
    def _copy(self):
        try: self.t.event_generate('<<Copy>>')
        except: pass
    def _paste(self):
        self.t.event_generate('<<Paste>>')
    def _sel(self):
        self.t.tag_add(tk.SEL,'1.0','end-1c')
        self.t.mark_set(tk.INSERT,'1.0'); self.t.see(tk.INSERT)
    def _dlp(self):
        c=self.t.get('1.0','end-1c')
        self.t.delete('1.0','end')
        self.t.insert('1.0','\n'.join(l.lstrip() for l in c.split('\n')))
    def _deL(self):
        c=self.t.get('1.0','end-1c')
        self.t.delete('1.0','end')
        self.t.insert('1.0','\n'.join(l for l in c.split('\n') if l.strip()))
    def _dis(self):
        c=re.sub(r'[ \t]+','',self.t.get('1.0','end-1c'))
        self.t.delete('1.0','end'); self.t.insert('1.0',c)
    def _md2html(self, strip_title=False):
        """MD转HTML按钮 - 手动将编辑区Markdown内容转换为HTML"""
        c = self.t.get('1.0', 'end-1c').strip()
        if not c:
            Msg.info("MD转HTML", "内容为空")
            return
        if not is_markdown_text(c):
            Msg.info("MD转HTML", "未检测到Markdown格式，跳过")
            return
        dom_pub = self.dv.get().strip().rstrip('/')
        base_url = dom_pub.replace('https://', '').replace('http://', '') if dom_pub else ''
        html = md_to_html(c, base_url, strip_title=strip_title)
        self.t.delete('1.0', 'end')
        self.t.insert('1.0', html)
        Msg.info("MD转HTML", "已转换为HTML")
    def _fmt(self):
        """规范按钮 - 按行首空格分割段落并添加<p></p>标签"""
        c=self.t.get('1.0','end-1c')
        has_p_tag = bool(re.search(r'<p\s*>', c))
        if has_p_tag:
            Msg.info("规范","已有<p>标签，保留原样")
            return
        lines = c.split('\n')
        paragraphs = []
        current_para = []
        for line in lines:
            if line.startswith(' ') or line == '':
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                    current_para = []
                if line == '':
                    paragraphs.append('')
            else:
                current_para.append(line)
        if current_para:
            paragraphs.append('\n'.join(current_para))
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        if not paragraphs:
            paragraphs = [c.strip()]
        r = []
        for p in paragraphs:
            r.append(f'<p>&nbsp&nbsp{p}</p>')
        self.t.delete('1.0','end')
        self.t.insert('1.0','\n\n'.join(r))
        w=self._hf(c,4)
        if w: self.t.insert('end',f'\n&nbsp&nbsp{w}。')
        Msg.info("规范","段落格式已规范")
    def _fmt2(self):
        """规范行首按钮 - 给有空行或行首空格的行前添加两个空格"""
        c=self.t.get('1.0','end-1c')
        lines = c.split('\n')
        result = []
        for i, line in enumerate(lines):
            if i > 0 and (lines[i-1].strip() == '' or lines[i-1].startswith(' ')):
                if not line.startswith(' '):
                    result.append('  ' + line)
                else:
                    result.append(line)
            else:
                result.append(line)
        self.t.delete('1.0','end')
        self.t.insert('1.0', '\n'.join(result))
        Msg.info("规范行首","行首空格已规范")
    def _hf(self,t,c):
        cc=re.findall(r'[\u4e00-\u9fff]{2,4}',t)
        ew=re.findall(r'\b[a-zA-Z]{3,}\b',t)
        wf={}
        for ch in cc: wf[ch]=wf.get(ch,0)+1
        for wd in ew: wl=wd.lower(); wf[wl]=wf.get(wl,0)+1
        sw=sorted(wf.items(),key=lambda x:x[1],reverse=True)
        tw=[w[0] for w in sw[:c]]
        return '，'.join(tw) if tw else ''
    def _count_chars(self, text):
        cn=sum(1 for c in text if '\u4e00'<=c<='\u9fff')
        en=sum(1 for c in text if c.isalpha())
        pn=sum(1 for c in text if c.isalnum() and not ('\u4e00'<=c<='\u9fff' or c.isalpha()))
        return cn,en,pn,cn+en+pn
    def _wcnt(self):
        ct=self.t.get('1.0','end-1c')
        cn,en,pn,total=self._count_chars(ct)
        cat=self.cv.get().strip()
        if not cat: Msg.info("提示","请先选择栏目"); return
        first_line=ct.split('\n')[0].strip() or '文章'
        t=self.tv.get().strip()
        if not t: t=first_line
        t=clean_title(t)
        self.tv.set(t)
        dom=self.dv.get().strip()
        has_cn=any('\u4e00'<=x<='\u9fff' for x in t)
        fb=c2p(re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9]','',t)) if has_cn else re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9]','',t)
        fb=sfn(fb) or 'article'
        pu=f'{dom.rstrip("/")}/{cat}/{fb}.html' if dom else f'/{cat}/{fb}.html'
        desc=get_first_words(ct,20,30).replace('<p>&nbsp&nbsp','').replace('</p>','')
        md_entry=f'[{t}]({pu} "{desc}")'
        url_file=os.path.join(PROGRAM_DIR,f'{cat}_url.txt')
        existing=''
        if os.path.exists(url_file):
            existing=read_file(url_file) or ''
        lines=[md_entry]+[l for l in existing.split('\n') if l.strip() and l!=md_entry]
        write_file(url_file,'\n'.join(lines))
        Msg.info("字数",f"统计: 汉字{cn} 字母{en} 数字{pn} 总计{total}\n已保存链接到 {cat}_url.txt")
    def _imp(self):
        fd=filedialog.askdirectory(title="选择文件夹",initialdir=WORK_DIR)
        if not fd: return
        tfs=[f for f in os.listdir(fd) if f.endswith('.txt')]
        if not tfs: Msg.info("导入","无TXT文件"); return
        date_pattern=r'20\d{2}\.\d{2}\.\d{2}'
        new6_pat=re.compile(r'^(.+)_([^_]+)_([^_]+)_([^_]+)_([0-9]+)_(' + date_pattern + r')\.txt$')
        old_pat=re.compile(r'^(.+)_(\d+)_(' + date_pattern + r')\.txt$')
        def key(f):
            m=new6_pat.match(f)
            if m: return int(m.group(5))
            m=old_pat.match(f)
            if m: return int(m.group(2))
            ns=re.findall(r'(\d+)',f)
            return int(ns[-1]) if ns else 0
        tfs.sort(key=key)
        total=len(tfs); ok_cnt=0; skip_cnt=0
        for i,fn in enumerate(tfs,1):
            fp=os.path.join(fd,fn)
            content=read_file(fp,errors='replace')
            if content is None:
                Msg.error("导入",f"[{i}/{total}] 读取失败，跳过: {fn}"); skip_cnt+=1; continue
            lines=content.split('\n')
            body='\n'.join(lines[1:]).lstrip('\n')
            first=(lines[0].strip() if lines else '')
            m6=new6_pat.match(fn)
            if m6:
                title=m6.group(1); author=m6.group(2); cat=m6.group(3); category=m6.group(4); num=m6.group(5); date_d=m6.group(6)
                if first: title=first
                if author: self.av.set(author)
                if cat: self.cv.set(cat)
                if category: self.cav.set(category)
                if not body: Msg.warn("导入",f"[{i}/{total}] 标题下无正文，跳过: {fn}"); skip_cnt+=1; continue
                if is_markdown_text(body):
                    dom_imp=self.dv.get().strip().rstrip('/')
                    body=md_to_html(body, dom_imp.replace('https://','').replace('http://','') if dom_imp else '', strip_title=True)
                    self.t.delete('1.0','end')
                    self.t.insert('1.0',f'{title}\n{body}')
                    Msg.info("导入",f"[{i}/{total}] Markdown已转HTML: {fn}")
                else:
                    self.t.delete('1.0','end')
                    self.t.insert('1.0',f'{title}\n{body}')
                self.tv.set(title)
                self._get_domain_list()
                self._pub(pub_date=f'{date_d[0:4]}年{date_d[5:7]}月{date_d[8:10]}日', skip_stxt=True, skip_orgf=True)
                if self.published: ok_cnt+=1
                else: skip_cnt+=1; Msg.warn("导入",f"[{i}/{total}] 未成功发布: {fn}")
            else:
                m5=old_pat.match(fn)
                if m5: num=m5.group(2)
                else:
                    ns=re.findall(r'(\d+)',fn)
                    num=ns[-1] if ns else None
                if num is not None and first==num:
                    Msg.warn("导入",f"[{i}/{total}] 首行为数字「{first}」，疑似无标题，跳过: {fn}"); skip_cnt+=1; continue
                t=first or fn[:-4]
                if not body: Msg.warn("导入",f"[{i}/{total}] 标题下无正文，跳过: {fn}"); skip_cnt+=1; continue
                self.t.delete('1.0','end')
                self.t.insert('1.0',f'{t}\n{body}')
                self.tv.set(t)
                self._get_domain_list()
                self._pub(skip_stxt=True, skip_orgf=True)
                if self.published: ok_cnt+=1
                else: skip_cnt+=1; Msg.warn("导入",f"[{i}/{total}] 未成功发布: {fn}")
        Msg.info("导入",f"完成：共{total}篇，成功发布{ok_cnt}篇，跳过{skip_cnt}篇")
    def _new(self):
        self.t.delete('1.0','end'); self.tv.set(''); self.cur=None
        self.published=False; self.pb.config(bg='#FF0000')
        self.ustack.clear(); self.rstack.clear()
    def _stxc(self):
        """TXT存按钮 - 保存到栏目-txt文件夹（带递增数字）"""
        t=self.tv.get().strip()
        c=self.t.get('1.0','end-1c').strip()
        if not c: Msg.info("提示","内容为空"); return
        if not t:
            fl=c.split('\n')[0].strip() if c else '未命名'
            t=sfn(fl) or '未命名'
        t=sfn(t) or '未命名'
        cat = self.cv.get().strip()
        if not cat:
            Msg.info("提示","请选择栏目"); return
        txt_dir_name = cat + '-txt'
        td = os.path.join(PROGRAM_DIR, txt_dir_name)
        if not os.path.exists(td): os.makedirs(td)
        date_str = datetime.now().strftime('%Y.%m.%d')
        # 全局递增：扫描目录下所有txt文件，找最大序号
        max_n = 0
        for f in os.listdir(td):
            m = re.match(r'^[^_]+_(\d+)_', f)
            if m:
                max_n = max(max_n, int(m.group(1)))
        fn = f'{t}_{max_n+1}_{date_str}.txt'
        # 检测重复文件（按标题去重）
        title_prefix = sfn(t)
        for f in os.listdir(td):
            if f.startswith(title_prefix) and f.endswith('.txt'):
                Msg.info("保存",f"标题已存在，跳过: {fn}")
                return
        try:
            write_file(os.path.join(td,fn), c)
            Msg.info("保存",f"已保存: {fn}")
        except Exception as e: Msg.error("保存",str(e))
    def _extract_top_words(self, text, n=5):
        """提取文本中的高频词"""
        text = text or ''
        import jieba
        from collections import Counter
        text = strip_html(text)
        text = re.sub(r'[#*`_\[\]~><-]', ' ', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        cn_words = list(jieba.cut(text))
        en_words = re.findall(r'[a-zA-Z]{2,}', text)
        stopwords = {'的','了','是','在','我','有','和','就','不','人','都','一','上','也','很','到','说','要','去','你','会','着','没有','看','好','自己','这','那','以','可','等','及','与','而','或','但','因','为','让','被','把','将','从','向','对','如','其','所','此','该','本','中','外','再','更','最','第','又','还','于','以及','可以','这个','那个','他们','我们','你们','什么','怎么','如何','这样','那样','一些','一个','python','js','css','html','a','an','the','is','are','was','were','be','been','being','have','has','had','do','does','did','will','would','shall','should','may','might','must','can','could','to','of','in','for','on','with','at','by','from','as','into','through','during','before','after','above','below','between','out','off','over','under','again','further','then','once','here','there','when','where','why','how','all','both','each','few','more','most','other','some','such','no','nor','not','only','own','same','so','than','too','very','s','t','just','don','now','i','me','my','we','our','you','your','he','him','his','she','her','it','its','they','them','their','what','which','who','whom','this','that','these','those','am','if','and','or','about','against','like','within','while'}
        filtered_cn = [w for w in cn_words if len(w.strip()) >= 2 and w.strip() not in stopwords]
        filtered_en = [w for w in en_words if w.lower() not in stopwords]
        cn_counter = Counter(filtered_cn)
        en_counter = Counter(filtered_en)
        top_cn = [w for w, _ in cn_counter.most_common(n)]
        top_en = [w for w, _ in en_counter.most_common(n)]
        combined = top_cn + top_en
        return combined[:n]

    def _orgf(self):
        """整理按钮 - 格式化+随机插入关键词/链接"""
        c=self.t.get('1.0','end-1c')
        if not c or not c.strip(): Msg.info("整理","内容为空"); return
        c=c.strip()

        top_words = self._extract_top_words(c, 5)

        lines = c.split('\n')
        paragraphs = []
        current_para = []
        in_p = False
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('<p>'):
                if current_para:
                    paragraphs.append((in_p, '\n'.join(current_para)))
                    current_para = []
                    in_p = False
                in_p = True
                current_para.append(line)
            elif stripped == '':
                if current_para:
                    paragraphs.append((in_p, '\n'.join(current_para)))
                    current_para = []
                    in_p = False
                paragraphs.append((False, ''))
            else:
                current_para.append(line)
        if current_para:
            paragraphs.append((in_p, '\n'.join(current_para)))

        r = []
        for wrapped, p in paragraphs:
            content = p.strip()
            if not content:
                r.append('')
                continue
            if not wrapped:
                lines_p = content.split('\n')
                wrapped_lines = []
                for lp in lines_p:
                    lp = lp.strip()
                    if not lp:
                        wrapped_lines.append('')
                        continue
                    if '<p>' in lp:
                        cp = re.sub(r'<p[^>]*>', '', lp)
                        cp = re.sub(r'</p>', '', cp)
                        wrapped_lines.append(f'<p>&nbsp&nbsp{cp}</p>')
                    else:
                        wrapped_lines.append(f'<p>&nbsp&nbsp{lp}</p>')
                r.append('\n'.join(wrapped_lines))
            else:
                r.append(p)
        formatted = '\n\n'.join(r).strip()
        while '\n\n\n' in formatted:
            formatted = formatted.replace('\n\n\n', '\n\n')

        self.t.delete('1.0', 'end')
        self.t.insert('1.0', formatted)

        chosen_kw = []
        kw_file = self.kv.get().strip()
        if kw_file:
            kp = os.path.join(PROGRAM_DIR, kw_file)
            if os.path.exists(kp):
                try:
                    c_kw = read_file(kp, errors='replace')
                    kls = [l.strip() for l in c_kw.split('\n') if l.strip()] if c_kw else []
                    if kls:
                        chosen_kw = random.sample(kls, min(3, len(kls)))
                except: pass

        if not chosen_kw and top_words:
            chosen_kw = random.sample(top_words, min(3, len(top_words)))

        if chosen_kw:
            ct = self.t.get('1.0', 'end-1c')
            ss = re.split(r'(?<=[。！？.!?])', ct)
            if len(ss) < 3:
                ss = re.split(r'(?<=[，,])', ct)
            positions = random.sample(range(len(ss)), min(3, len(ss)))
            for i, pos in enumerate(reversed(sorted(positions))):
                start = sum(len(s) for s in ss[:pos])
                sentence = ss[pos]
                insert_point = start + len(sentence)
                suffix = '' if i == 2 else '，'
                self.t.insert(f'1.0+{insert_point}chars', f'{chosen_kw[i]}{suffix}')
        cat = self.cv.get().strip()
        if cat:
            cd = os.path.join(PROGRAM_DIR, cat)
            uf = os.path.join(cd, 'url.txt')
            if os.path.exists(uf):
                try:
                    c_urls = read_file(uf, errors='replace')
                    uls = c_urls.split('\n') if c_urls else []
                    uls = [l.strip() for l in uls if l.strip()]
                    if uls:
                        chosen = random.sample(uls, min(2, len(uls)))
                        ct = self.t.get('1.0','end-1c')
                        ss = re.split(r'(?<=[。！？.!?])', ct)
                        for link in chosen:
                            if ss:
                                ts = random.choice(ss)
                                cps = [m.start() for m in re.finditer(r'，', ts)]
                                if cps:
                                    oc = self.t.get('1.0','end-1c')
                                    ip = oc.find(ts)
                                    if ip >= 0:
                                        self.t.insert(f'1.0+{ip+random.choice(cps)}chars', f'{link}，<br>')
                except: pass
            cd = os.path.join(PROGRAM_DIR, cat)
            uf = os.path.join(cd, 'url.txt')
            if os.path.exists(uf):
                try:
                    c_urls = read_file(uf, errors='replace')
                    uls = c_urls.split('\n') if c_urls else []
                    uls = [l.strip() for l in uls if l.strip()]
                    if uls:
                        cnt = min(6, len(uls))
                        chosen = random.sample(uls, cnt)
                        for link in chosen:
                            self.t.insert('end', f'\n{link}')
                        self.t.insert('end', '<br>')
                except: pass

        if top_words:
            keyword_line = '，'.join(top_words[:5]) + '。<br>'
            self.t.insert('end', f'\n{keyword_line}')

        Msg.info("整理","完成")
    def _undo(self):
        if not self.ustack: return
        self.rstack.append(self.t.get('1.0','end-1c'))
        self.t.delete('1.0','end'); self.t.insert('1.0',self.ustack.pop())
    def _redo(self):
        if not self.rstack: return
        self.ustack.append(self.t.get('1.0','end-1c'))
        self.t.delete('1.0','end'); self.t.insert('1.0',self.rstack.pop())
    def _r3(self):
        r=tk.Frame(self.tb,bg='#9400D3'); r.pack(fill=tk.X,padx=2,pady=2)
        tk.Label(r,text="标题:",bg='#9400D3',fg='white',
                font=('宋体',10,'bold')).pack(side=tk.LEFT,padx=(5,2))
        self.tv=tk.StringVar()
        def on_title_change(*args):
            v=self.tv.get()
            if v != clean_title(v):
                self.tv.set(clean_title(v))
        self.tv.trace_add('write', on_title_change)
        tk.Entry(r,textvariable=self.tv,width=10,bg='white',
                font=('宋体',10)).pack(side=tk.LEFT,padx=2)
        def paste_title():
            try: self.tv.set(self.root.clipboard_get())
            except: Msg.info("提示","剪贴板为空")
        tk.Button(r,text="粘贴",command=paste_title,
                 bg='#FF8C00',width=4,font=('宋体',9)).pack(side=tk.LEFT,padx=2)
        tk.Label(r,text="链接:",bg='#9400D3',fg='white',
                font=('宋体',10,'bold')).pack(side=tk.LEFT,padx=(10,2))
        self.lv=tk.StringVar()
        tk.Entry(r,textvariable=self.lv,width=15,bg='white',
                font=('宋体',10)).pack(side=tk.LEFT,padx=2)
        tk.Button(r,text="确定",command=self._lk,bg='#9ACD32',
                 width=4,font=('宋体',9)).pack(side=tk.LEFT,padx=2)
        tk.Label(r,text="关键词:",bg='#9400D3',fg='white',
                font=('宋体',10,'bold')).pack(side=tk.LEFT,padx=(10,2))
        self.kv=tk.StringVar()
        self.kc=ttk.Combobox(r,textvariable=self.kv,values=[],
                             state='readonly',width=8)
        self.kc.pack(side=tk.LEFT,padx=2)
        tk.Button(r,text="确定",command=self._kw,bg='#9ACD32',
                 width=4,font=('宋体',9)).pack(side=tk.LEFT,padx=2)
        tk.Label(r,text="栏目:",bg='#9400D3',fg='white',
                font=('宋体',10,'bold')).pack(side=tk.LEFT,padx=(10,2))
        self.cv=tk.StringVar()
        self.cc=ttk.Combobox(r,textvariable=self.cv,values=[],
                             state='readonly',width=4)
        self.cc.pack(side=tk.LEFT,padx=2)
        tk.Button(r,text="确定",command=self._cat,bg='#9ACD32',
                 width=4,font=('宋体',9)).pack(side=tk.LEFT,padx=2)
        tk.Label(r,text="域名:",bg='#9400D3',fg='white',
                font=('宋体',10,'bold')).pack(side=tk.LEFT,padx=(10,2))
        self.dv=tk.StringVar()
        self.dc=ttk.Combobox(r,textvariable=self.dv,values=[],
                             state='normal',width=12)
        self.dc.pack(side=tk.LEFT,padx=2)
        tk.Label(r,text="作者:",bg='#9400D3',fg='white',
                font=('宋体',10,'bold')).pack(side=tk.LEFT,padx=(10,2))
        self.av=tk.StringVar()
        self.ac=ttk.Combobox(r,textvariable=self.av,values=[],
                             state='readonly',width=8)
        self.ac.pack(side=tk.LEFT,padx=2)
        tk.Label(r,text="分类:",bg='#9400D3',fg='white',
                font=('宋体',10,'bold')).pack(side=tk.LEFT,padx=(10,2))
        self.cav=tk.StringVar()
        self.cac=ttk.Combobox(r,textvariable=self.cav,values=[],
                              state='readonly',width=8)
        self.cac.pack(side=tk.LEFT,padx=2)
    def _lk(self):
        url=self.lv.get().strip()
        if not url: Msg.info("提示","输入网址"); return
        cat=self.cv.get().strip()
        if not cat: Msg.info("提示","选择栏目"); return
        ct=self.t.get('1.0','end-1c')
        fl=ct.split('\n')[0].strip() if ct else '标题'
        tl=fl[:30]+('...' if len(fl)>30 else '')
        sn=fl[:20] or '文章'
        l=f'<a href="{url}" target="_blank" title="{tl}">{sn}</a>'
        cd=os.path.join(PROGRAM_DIR,cat)
        if not os.path.exists(cd): os.makedirs(cd)
        tp=os.path.join(cd,f'{cat}.txt')
        try:
            ex=''
            if os.path.exists(tp):
                ex = read_file(tp) or ''
            write_file(tp, l+'<br>\n'+ex)
            Msg.info("链接","已添加")
        except Exception as e: Msg.error("错误",str(e))
    def _kw(self):
        kw=self.kv.get().strip()
        if not kw: Msg.info("提示","选择关键词"); return
        # 确保有.txt后缀
        if not kw.endswith('.txt'):
            kw = kw + '.txt'
        kp=os.path.join(PROGRAM_DIR,kw)
        if not os.path.exists(kp): Msg.info("提示","文件不存在"); return
        try:
            c_kw = read_file(kp, errors='replace')
            if c_kw is None: return
            ls=[l.strip() for l in c_kw.split('\n') if l.strip()]
            c=self.t.get('1.0','end-1c')
            if not ls:
                ls=self._extract_top_words(c, 3)
                if not ls: Msg.info("提示","无法提取关键词"); return
            cnt=min(3,len(ls))
            ch=random.sample(ls,cnt); ins=0
            ss=re.split(r'(?<=[。！？.!?])',c)
            for wd in ch:
                if ss:
                    ts=random.choice(ss)
                    cps=[m.start() for m in re.finditer(r'，',ts)]
                    if cps:
                        oc=self.t.get('1.0','end-1c'); ip=oc.find(ts)
                        if ip>=0:
                            self.t.insert(f'1.0+{ip+random.choice(cps)}chars',f'{wd}，')
                            ins+=1
            Msg.info("关键词",f"已插入{ins}条" if ins else "无合适位置")
        except Exception as e: Msg.error("错误",str(e))
    def _cat(self):
        cat=self.cv.get().strip()
        if not cat: Msg.info("提示","选择栏目"); return
        cd=os.path.join(PROGRAM_DIR,cat)
        uf=os.path.join(cd,'url.txt')
        if not os.path.exists(uf): Msg.info("提示","无url.txt"); return
        try:
            c_urls = read_file(uf, errors='replace')
            uls = c_urls.split('\n') if c_urls else []
            ls = [l.strip() for l in uls if l.strip()]
            if not ls: Msg.info("提示","url.txt为空"); return
            cnt=min(5,len(ls))
            self.t.insert('end','\n\n'+'\n'.join(
                f'<p>{l}</p>' for l in random.sample(ls,cnt))+'<br>')
            Msg.info("栏目",f"已插入{cnt}个链接")
        except Exception as e: Msg.error("错误",str(e))
    def _load(self):
        # 读取各配置文件的选项值
        config_files = {
            'domain.txt': 'dv',
            '关键词.txt': 'kv',
            '栏目.txt': 'cv',
            '作者.txt': 'av',
            '分类.txt': 'cav'
        }
        for fn, key in config_files.items():
            fp = os.path.join(PROGRAM_DIR, fn)
            vals = []
            if os.path.exists(fp):
                try:
                    c_vals = read_file(fp)
                    if c_vals:
                        vals = [l.strip() for l in c_vals.split('\n') if l.strip()]
                except:
                    pass
            attr_name = {'dv': 'dc', 'kv': 'kc', 'cv': 'cc', 'av': 'ac', 'cav': 'cac'}[key]
            cb = getattr(self, attr_name)
            cb['values'] = vals
            if vals:
                cb.set(vals[0])

        # 动态加载关键词文件内容到下拉框（去掉.txt后缀）
        kw_fp = os.path.join(PROGRAM_DIR, '关键词.txt')
        kw_vals = []
        if os.path.exists(kw_fp):
            try:
                c_kw = read_file(kw_fp)
                if c_kw:
                    kw_vals = [l.strip().replace('.txt', '') for l in c_kw.split('\n') if l.strip()]
            except:
                pass
        self.kc['values'] = kw_vals
        if kw_vals:
            self.kv.set(kw_vals[0])
    def _bind(self):
        for k,c in [('n',self._new),('o',self._open),('s',self._save),
                    ('z',self._undo),('y',self._redo),('a',self._sel)]:
            self.root.bind(f'<Control-{k}>',lambda e,c=c:c())
            self.root.bind(f'<Control-{k.upper()}>',lambda e,c=c:c())
        self.root.bind('<Control-Shift-S>',lambda e:self._sav2())
    def _open(self):
        fp=filedialog.askopenfilename(title="打开",
            filetypes=[("文本","*.txt *.html *.htm *.md"),("*","*.*")],
            initialdir=self.last_access_path)
        if not fp: return
        try:
            c = read_file(fp, errors='replace')
            self.t.delete('1.0','end'); self.t.insert('1.0',c)
            self.cur=fp
            self.tv.set(os.path.splitext(os.path.basename(fp))[0])
            self.last_access_path = os.path.dirname(fp)
            Msg.info("打开",f"已打开: {os.path.basename(fp)}")
        except Exception as e: Msg.error("打开",str(e))
    def _save(self):
        if self.cur:
            try:
                write_file(self.cur, self.t.get('1.0','end-1c'))
                Msg.info("保存","已保存")
            except Exception as e: Msg.error("保存",str(e))
        else: self._sav2()
    def _sav2(self):
        fp=filedialog.asksaveasfilename(title="另存为",defaultextension=".txt",
            filetypes=[("文本","*.txt"),("HTML","*.html"),("*","*.*")],
            initialdir=self.last_access_path)
        if not fp: return
        try:
            write_file(fp, self.t.get('1.0','end-1c'))
            self.cur=fp; Msg.info("另存为","已保存")
        except Exception as e: Msg.error("保存",str(e))
    def _apply(self):
        s = {
            'font_family': self.DEFAULT_FONT_FAMILY,
            'font_size': self.DEFAULT_FONT_SIZE,
            'font_weight': self.DEFAULT_FONT_WEIGHT,
            'font_slant': self.DEFAULT_FONT_SLANT,
            'text_color': self.DEFAULT_TEXT_COLOR,
            'bg_color': self.DEFAULT_BG_COLOR,
        }
        self.t.config(font=(s['font_family'],s['font_size'],
                           s['font_weight'],s['font_slant']),
                     fg=s['text_color'],bg=s['bg_color'])
        self.root.configure(bg=s['bg_color'])
    def _setd(self):
        pass
    def _get_date_str(self):
        return datetime.now().strftime('%Y年%m月%d日')
    def _get_domain_list(self):
        fp = os.path.join(PROGRAM_DIR, 'domain.txt')
        dl = []
        if os.path.exists(fp):
            dl = [l.strip() for l in (read_file(fp, errors='replace') or '').split('\n') if l.strip()]
        self.dc['values'] = dl
        if dl and self.dv.get().strip() not in dl:
            self.dv.set(dl[0])
        return dl

    def _pubbtn(self):
        self.published=False
        self.pb.config(bg='#FF8C00')
        c=self.t.get('1.0','end-1c').strip()
        if c and is_markdown_text(c):
            self._md2html()
        self._pub()
    def _pub(self, pub_date=None, skip_stxt=False, skip_orgf=False):
        """发布文章 - 先执行txt和整理功能"""
        c=self.t.get('1.0','end-1c').strip()
        if not c: Msg.info("提示","内容为空"); return
        if not get_min_pubs(c, 300):
            Msg.warn("发布跳过",f"正文汉字不足300字，跳过发布。请补充正文后再发布。")
            return
        first_line=c.split('\n')[0].strip() or '文章'
        t=self.tv.get().strip()
        if not t:
            t=first_line
            self.tv.set(t)
        t = clean_title(t)
        self.tv.set(t)
        if not skip_stxt: self._stxt()
        if not skip_orgf: self._orgf()
        c=self.t.get('1.0','end-1c').strip()
        if not pub_date:
            pub_date = datetime.now().strftime('%Y年%m月%d日')
        dom_pub=self.dv.get().strip().rstrip('/')
        if is_markdown_text(c):
            dom_pub_now = self.dv.get().strip().rstrip('/')
            base_url = dom_pub_now.replace('https://', '').replace('http://', '') if dom_pub_now else ''
            c = md_to_html(c, base_url, strip_title=True)
            self.t.delete('1.0', 'end')
            self.t.insert('1.0', c)
            Msg.info("Markdown", "已转换为HTML（去除重复主标题）")
        title_text = get_first_words(c, 20, 30)
        abstract_text = get_first_words(c, 150, 200)
        md_title = get_first_words(c, 25, 35)
        md_abstract = get_first_words(c, 150, 200)
        demo=os.path.join(PROGRAM_DIR,'demo','demo.html')
        if not os.path.exists(demo):
            Msg.error("发布失败","请创建 demo/demo.html"); return
        cat=self.cv.get().strip()
        if not cat: Msg.info("提示","请选栏目"); return
        cd=os.path.join(PROGRAM_DIR,cat)
        if not os.path.exists(cd): os.makedirs(cd)
        ct=re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9]','',t)
        ct=ct.replace(' ','').replace('\u3000','')
        has_cn=any('\u4e00'<=x<='\u9fff' for x in t)
        fb=c2p(ct) if has_cn else ct
        fb=sfn(clean_filename(fb)) or 'article'
        hfn=fb+'.html'; hfp=os.path.join(cd,hfn)
        try:
            tpl = read_file(demo)
            dom=self.dv.get().strip()
            ht=tpl
            ht=ht.replace('title_name',ct)
            ht=ht.replace('<title>title_name</title>',f'<title>{ct}</title>')
            ht=ht.replace('网页标题',t)
            ht=ht.replace('<h1>文章标题</h1>',f'<h1>{t}</h1><span class="article-date" style="font-size:14px">{pub_date}|作者:{self.av.get().strip()}|栏目:{cat}|分类:{self.cav.get().strip()}</span>')
            desc = get_first_words(c, 25, 30).replace('<p>&nbsp&nbsp','').replace('</p>','')
            ht=ht.replace('描述',desc)
            iuf_cat=os.path.join(PROGRAM_DIR,f'{cat}_url.txt')
            if os.path.exists(iuf_cat):
                try:
                    cat_lines=[l.strip() for l in read_file(iuf_cat,errors='replace').split('\n') if l.strip() and l.strip().startswith('<a')]
                    if cat_lines:
                        first_link=cat_lines[0]
                        nav_html=f'下一页 <span>{first_link}</span>'
                        ht=ht.replace('<!-- page_nav_link-->',nav_html)
                except: pass
            top_words = self._extract_top_words(c, 5)
            if top_words:
                kw_str = '，'.join(top_words)
                ht=ht.replace('{关键词}',kw_str)
                ht=ht.replace('关键词',kw_str)
            if '<p>' in c:
                formatted_article = c.strip().replace('{','').replace('}','')
            else:
                paragraphs = re.split(r'\n\s*\n', c)
                formatted_article = '\n'.join([f'<p>&nbsp&nbsp{p.strip()}</p>' for p in paragraphs if p.strip()]).replace('{','').replace('}','')
            ht=re.sub(r'<!-- site_page_begin -->.*?<!-- site_page_end -->',
                      lambda m:f'<!-- site_page_begin -->\n{formatted_article}\n            <!-- site_page_end -->',
                      ht,flags=re.DOTALL)
            uf5=os.path.join(PROGRAM_DIR,f'{cat}_url.txt')
            uls5=[]
            if os.path.exists(uf5):
                c_urls5 = read_file(uf5, errors='replace')
                if c_urls5:
                    uls5=[l.strip() for l in c_urls5.split('\n') if l.strip() and l.strip().startswith('<a')]
            if uls5:
                last_5_links = '\n'.join(uls5[:min(5,len(uls5))])
                ht = ht.replace('<!-- site_page_end -->', last_5_links+'\n            <!-- site_page_end -->')
            uf=os.path.join(PROGRAM_DIR,f'{cat}_url.txt')
            uls=[]
            if os.path.exists(uf):
                c_urls = read_file(uf, errors='replace')
                if c_urls:
                    uls=[l.strip() for l in c_urls.split('\n') if l.strip()]
            if uls:
                link_content = '\n'.join(uls[:min(8,len(uls))])
            else:
                link_content = ''
            if not link_content:
                ht=re.sub(r'<!-- new_link_name_start-->.*?<!-- new_link_name_end-->', '', ht, flags=re.DOTALL)
            else:
                ht=re.sub(r'<!-- new_link_name_start-->.*?<!-- new_link_name_end-->',
                          lambda m:link_content, ht, flags=re.DOTALL)
            ium=os.path.join(PROGRAM_DIR,f'{cat}_index_url.md')
            ium_old=os.path.join(PROGRAM_DIR,f'{cat}-index_url.md')
            existing_md=read_file(ium) if os.path.exists(ium) else ''
            dup_title=False; dup_content=False
            if existing_md:
                for line in existing_md.split('\n'):
                    line=line.strip()
                    if not line or not line.startswith('<h2'): continue
                    mt=re.search(r'>([^<]+)</a\s*>',line)
                    if mt and mt.group(1).strip()==t:
                        dup_title=True; break
            if not dup_title and existing_md:
                for item in existing_md.split('<!-- site_page -->')[1:]:
                    if item.strip():
                        ic=re.sub(r'<[^>]+>','',item)
                        if ic.strip()==c.strip():
                            dup_content=True; break
            if dup_title:
                Msg.warn("重复发布","标题「{0}」已存在，跳过发布".format(t))
                return
            if dup_content:
                Msg.warn("重复发布","该文章正文已发布过，跳过")
                return
            def file_has_hfn(filepath):
                if not os.path.exists(filepath): return False
                content = read_file(filepath) or ''
                for line in content.split('\n'):
                    line = line.strip()
                    if not line: continue
                    if hfn in line: return True
                return False
            dup_files = []
            if file_has_hfn(os.path.join(PROGRAM_DIR, f'{cat}_index_url.txt')):
                dup_files.append(f'{cat}_index_url.txt')
            if file_has_hfn(os.path.join(PROGRAM_DIR, f'{cat}_index_url.md')):
                dup_files.append(f'{cat}_index_url.md')
            if file_has_hfn(os.path.join(PROGRAM_DIR, f'{cat}_url.txt')):
                dup_files.append(f'{cat}_url.txt')
            if dup_files:
                Msg.warn("文件名重复",f"文件名「{hfn}」已在以下文件中存在，跳过写入: {', '.join(dup_files)}")
                return
            # about_link_list: 从{cat}_url.txt随机取6条<a>链接，插入模板标记之间
            about_begin='<!-- about_link_list_begin -->'
            about_end='<!-- about_link_list_end -->'
            if about_begin in ht and about_end in ht:
                cat_url_file=os.path.join(PROGRAM_DIR,f'{cat}_url.txt')
                about_links=[]
                if os.path.exists(cat_url_file):
                    alines=[l.strip() for l in read_file(cat_url_file, errors='replace').split('\n') if l.strip() and l.strip().startswith('<a')]
                    if alines:
                        n=min(6,len(alines))
                        about_links=random.sample(alines,n) if len(alines)>n else alines
                about_block=''.join(link+'<br>\n' for link in about_links)
                ht=re.sub(r'<!-- about_link_list_begin -->.*?<!-- about_link_list_end -->',
                          lambda m:about_begin+'\n'+about_block+about_end,
                          ht,flags=re.DOTALL)
            write_file(hfp, ht)
            pu=f'{dom.rstrip("/")}/{cat}/{hfn}' if dom else f'/{cat}/{hfn}'
            title_text_clean = re.sub(r'<[^>]+>', '', title_text).strip()
            lh=f'<a href="{pu}" target="_blank" title="{title_text_clean}" style="color:#555860">{t}</a>'
            ruf=os.path.join(PROGRAM_DIR,'url.txt')
            er=read_file(ruf) or ''
            lines=[lh]+[l for l in er.split('\n') if l.strip() and l!=lh]
            write_file(ruf, '\n'.join(lines))
            iuf=os.path.join(PROGRAM_DIR,f'{cat}_index_url.txt')
            ei=''
            if not os.path.exists(iuf):
                write_file(iuf, pu)
            else:
                ei = read_file(iuf)
                elines=[l for l in ei.split('\n') if l.strip()]
                if pu not in elines:
                    elines.insert(0, pu)
                write_file(iuf, '\n'.join(elines))
            udf=os.path.join(PROGRAM_DIR,f'{cat}_url.txt')
            ed=read_file(udf) or ''
            ulines=[lh]+[l for l in ed.split('\n') if l.strip() and l!=lh]
            write_file(udf, '\n'.join(ulines))
            self._sitemap(pu, cat)
            if os.path.exists(ium_old) and not os.path.exists(ium):
                write_file(ium, read_file(ium_old))
            ciu=os.path.join(PROGRAM_DIR,f'{cat}_index_url.txt')
            fun=''
            if os.path.exists(ciu):
                c_ciu = read_file(ciu)
                if c_ciu:
                    for line in c_ciu.split('\n'):
                        line=line.strip()
                        if line.startswith('<a') and '</a>' in line:
                            fun=line; break
            url_name = fun or pu
            url_name_clean = re.sub(r'<[^>]+>', '', url_name).strip()
            title_text_clean = re.sub(r'<[^>]+>', '', title_text).strip()
            md_title_clean = re.sub(r'<[^>]+>', '', md_title).strip().replace('#','')
            md_abstract_clean = re.sub(r'<[^>]+>', '', md_abstract).strip()
            current_date = pub_date
            md_entry = f"""<!-- site_page -->
   <div class="article-item">
   <h2 class="article-title">
   <a href="{url_name_clean}" target="_blank" title="{md_title_clean}" style="color:#555860">{t}</a >
   </h2>
   <div class="article-meta">
   {current_date}|作者:{self.av.get().strip()}|栏目:{cat}|分类:{self.cav.get().strip()}
   </div>
   <p class="article-desc">
   {md_abstract_clean.replace('{','').replace('}','')}
   </p>
   </div>"""
            em=''
            if os.path.exists(ium):
                em = read_file(ium)
            ium_new=md_entry+'\n'+em
            write_file(ium, ium_new)
            iuall=os.path.join(PROGRAM_DIR,'index_url_all.md')
            iall=read_file(iuall) if os.path.exists(iuall) else ''
            write_file(iuall, ium_new+'\n'+iall if iall else ium_new)
            self.published=True; self.pb.config(bg='#00FF00')
            import json as _json
            _lpub={'hfp':hfp,'hfn':hfn,'pu':pu,'cat':cat,'date':datetime.now().strftime('%Y-%m-%d')}
            try:
                _lpub['txt_file']=getattr(self,'_last_txt_fn','')
                if not os.path.exists(_lpub['txt_file']): _lpub['txt_file']=''
            except: _lpub['txt_file']=''
            write_file(os.path.join(PROGRAM_DIR,'last_pub.json'),_json.dumps(_lpub,ensure_ascii=False))
            self._gen_sitemap(t, pu)
            Msg.info("发布成功",f"已发布: {hfp}")
        except Exception as e:
            import traceback
            Msg.error("发布失败",str(e)+'\n'+traceback.format_exc())
    def _gen_sitemap(self, title, pu):
        """生成 sitemap.txt 到程序目录（新链接在最前面）"""
        try:
            sm_link = f'[{title}]({pu})'
            sm_file = os.path.join(PROGRAM_DIR, 'sitemap.txt')
            sm_existing = ''
            if os.path.exists(sm_file):
                sm_existing = read_file(sm_file) or ''
            lines = [sm_link] + [l for l in sm_existing.split('\n') if l.strip() and l != sm_link]
            write_file(sm_file, '\n'.join(lines))
        except Exception:
            pass
    def _sitemap(self, url, cat=''):
        sf = os.path.join(PROGRAM_DIR, cat, 'sitemap.xml') if cat else os.path.join(PROGRAM_DIR, 'sitemap.xml')
        now=datetime.now().strftime('%Y-%m-%d')
        url_esc=url.replace('&','&amp;')
        en=(f'  <url>\n    <loc>{url_esc}</loc>\n    <lastmod>{now}</lastmod>\n'
            f'    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>')
        if os.path.exists(sf):
            ex = read_file(sf)
            if url in ex: return
            write_file(sf, ex.replace('</urlset>',en+'\n</urlset>'))
        else:
            write_file(sf, '<?xml version="1.0" encoding="UTF-8"?>\n'
                       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                       +en+'\n</urlset>')
        if cat:
            rsf=os.path.join(PROGRAM_DIR,'sitemap.xml')
            if url in (read_file(rsf) or ''): return
            if os.path.exists(rsf):
                rex=read_file(rsf)
                m=re.search(r'(?m)^\s*<url>', rex)
                if m:
                    rex=rex[:m.start()]+en+'\n'+rex[m.start():]
                else:
                    rex=rex.replace('</urlset>', en+'\n</urlset>')
                write_file(rsf, rex)
            else:
                write_file(rsf, '<?xml version="1.0" encoding="UTF-8"?>\n'
                       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                       +en+'\n</urlset>')
    def _unpub(self):
        last=os.path.join(PROGRAM_DIR,'last_pub.json')
        if not os.path.exists(last):
            Msg.info("撤销发布","没有找到最近一次发布的记录"); return
        try:
            import json
            rec=json.loads(read_file(last))
        except Exception:
            Msg.error("撤销发布","last_pub.json 解析失败"); return
        removed=[]
        def rmline(path,needle):
            if not os.path.exists(path): return
            ls=[l for l in (read_file(path,errors='replace') or '').split('\n')
                if l.strip() and needle not in l]
            write_file(path,'\n'.join(ls))
        def rm_md_path(path,needle):
            if not os.path.exists(path) or not needle: return
            c=read_file(path,errors='replace') or ''
            parts=c.split('<!-- site_page -->')
            head,rest=parts[0],parts[1:]
            new_rest=[]
            for i in rest:
                if needle in i:
                    continue
                new_rest.append(i)
            if new_rest:
                write_file(path,head+'<!-- site_page -->'.join(new_rest))
            else:
                write_file(path,head.rstrip())
        def rm_sitemap(sf,url):
            if not os.path.exists(sf) or not url: return
            c=read_file(sf,errors='replace') or ''
            if url in c:
                ue='  <url>\n    <loc>'+url.replace('&','&amp;')+'</loc>\n    <lastmod>'
                ie=c.find(ue)
                if ie>=0:
                    je=c.find('  </url>',ie)
                    if je>=0:
                        end=je+len('  </url>')
                        if c[end:end+1]=='\n': end+=1
                        c=c[:ie]+c[end:]
                write_file(sf,c)
        if rec.get('hfp') and os.path.exists(rec['hfp']):
            os.remove(rec['hfp']); removed.append(os.path.basename(rec['hfp']))
        if rec.get('txt_file') and os.path.exists(rec['txt_file']):
            os.remove(rec['txt_file']); removed.append(os.path.basename(rec['txt_file']))
        hfn=rec.get('hfn',''); pu=rec.get('pu',''); cat=rec.get('cat','')
        if hfn:
            for f in [f'/{cat}_index_url.txt',f'/{cat}_url.txt','/url.txt']:
                rmline(os.path.join(PROGRAM_DIR,f.lstrip('/')),hfn)
        if pu:
            rm_sitemap(os.path.join(PROGRAM_DIR,cat,'sitemap.xml'),pu)
            rm_sitemap(os.path.join(PROGRAM_DIR,'sitemap.xml'),pu)
        if hfn and cat:
            rm_md_path(os.path.join(PROGRAM_DIR,f'{cat}_index_url.md'),hfn)
            rm_md_path(os.path.join(PROGRAM_DIR,'index_url_all.md'),hfn)
        os.remove(last)
        self.published=False; self.pb.config(bg='#FF0000')
        Msg.info("撤销发布",f"已撤销最近一次发布: {', '.join(removed) or rec.get('hfn','')}\n链接/索引文件中的对应条目已删除")
    def _home(self):
        """生成首页 - 完整分页"""
        cat=self.cv.get().strip()
        if not cat: Msg.info("提示","请选栏目"); return
        cd=os.path.join(PROGRAM_DIR,cat)
        ih=os.path.join(cd,'index.html')
        demo=os.path.join(PROGRAM_DIR,'demo','index.html')
        if not os.path.exists(demo):
            if not os.path.exists(ih):
                Msg.error("错误","请创建demo/index.html"); return
            ic=read_file(ih)
        else:
            ic=read_file(demo)
        ium=os.path.join(PROGRAM_DIR,f'{cat}_index_url.md')
        ium_old=os.path.join(PROGRAM_DIR,f'{cat}-index_url.md')
        if os.path.exists(ium_old) and not os.path.exists(ium):
            write_file(ium, read_file(ium_old))
        all_items=[]
        seen_urls=set()
        if os.path.exists(ium):
            try:
                mc = read_file(ium)
                raw_items=[item for item in mc.split('<!-- site_page -->')[1:] if item.strip()]
                for item in raw_items:
                    item=item.replace('{','').replace('}','')
                    url_match=re.search(r'href="([^"]+)"',item)
                    url=url_match.group(1) if url_match else None
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_items.append(item)
                    elif not url and item not in all_items:
                        all_items.append(item)
            except: pass
        page_size=30; total=len(all_items); pages=(total+page_size-1)//page_size
        dom=self.dv.get().strip() or 'localhost'
        cat_safe=sfn(cat)
        uf=os.path.join(PROGRAM_DIR,f'{cat}_url.txt')
        side_links=''
        if os.path.exists(uf):
            try:
                c_urls=read_file(uf, errors='replace')
                uls=[l.strip() for l in c_urls.split('\n') if l.strip() and l.strip().startswith('<a') and '</a>' in l.strip()]
                if uls:
                    cnt=min(6,len(uls))
                    side_links='\n'.join(random.sample(uls, cnt))
            except: pass
        def fill_side(html):
            if not side_links: return html
            return re.sub(r'<!-- new_link_name_start-->.*?<!-- new_link_name_end-->',
                         lambda m:f'<!-- new_link_name_start-->\n{side_links}\n        <!-- new_link_name_end-->',
                         html, flags=re.DOTALL)
        def build_page_on(base, pi):
            s=pi*page_size; e=min(s+page_size,total)
            cards='\n'.join(f'<!-- site_page -->\n{item}' for item in all_items[s:e])
            # 先清除占位符之间的旧内容，再插入最新30条
            pc=re.sub(r'<!-- site_page_begin -->.*?<!-- site_page_end -->',
                      lambda m:f'<!-- site_page_begin -->\n{cards}\n            <!-- site_page_end -->',
                      base, flags=re.DOTALL)
            nav=''
            if pi==0:
                if pages>1:
                    nav=f'<a href="{dom}_{cat_safe}_index_1.html" aria-label="下一页">下一页</a>'
            else:
                if pi==1:
                    nav+=f'<a href="index.html" aria-label="上一页">上一页</a> '
                elif pi>1:
                    nav+=f'<a href="{dom}_{cat_safe}_index_{pi-1}.html" aria-label="上一页">上一页</a> '
                if pi+1<pages:
                    nav+=f'<a href="{dom}_{cat_safe}_index_{pi+1}.html" aria-label="下一页">下一页</a>'
            pc=pc.replace('<a href="page_nav_link" aria-label="下一页">下一页</a>',nav)
            pc=re.sub(r'<!-- page_nav_link-->',lambda m:nav,pc)
            return fill_side(pc)
        build_page=lambda pi: build_page_on(read_file(demo) if os.path.exists(demo) else ic, pi)
        if not all_items:
            base=read_file(demo) if os.path.exists(demo) else ic
            base=re.sub(r'<!-- site_page_begin -->.*?<!-- site_page_end -->',
                        '<!-- site_page_begin -->\n            <!-- site_page_end -->',
                        base, flags=re.DOTALL)
            write_file(ih, fill_side(base))
            Msg.info("首页","已生成（无内容）"); return
        if total<=page_size:
            write_file(ih, build_page(0))
            Msg.info("首页",f"已生成index.html（{total}条内容，未超30条不分页）")
            return
        # 内容超过30条：index.html复制demo重新生成第1页，其余页另存为{域名}_{栏目}_index_{递增id}.html
        base1=read_file(demo) if os.path.exists(demo) else ic
        write_file(ih, build_page_on(base1, 0))
        for pi in range(1, pages):
            basep=read_file(demo) if os.path.exists(demo) else base1
            write_file(os.path.join(cd,f'{dom}_{cat_safe}_index_{pi}.html'), build_page_on(basep, pi))
        # 清理旧的分页文件（id超出当前页数的），防止残留
        pats=re.compile(r'^' + re.escape(dom) + r'_' + re.escape(cat_safe) + r'_index_([0-9]+)\.html$')
        for f in os.listdir(cd):
            m=pats.match(f)
            if m and int(m.group(1))>=pages:
                try: os.remove(os.path.join(cd,f))
                except: pass
        Msg.info("首页",f"已生成index.html+{pages-1}个分页文件（共{pages}页，{total}条内容）")
    def _program_home(self):
        """生成程序目录index.html及分页 - 基于index_url_all.md每30条分页"""
        iuall=os.path.join(PROGRAM_DIR,'index_url_all.md')
        if not os.path.exists(iuall):
            Msg.error("程序首页","index_url_all.md 不存在"); return
        iuh=os.path.join(PROGRAM_DIR,'index.html')
        demop=os.path.join(PROGRAM_DIR,'demo','index.html')
        base_demo=read_file(demop) if os.path.exists(demop) else None
        if not os.path.exists(iuh):
            if not base_demo:
                Msg.error("程序首页","程序目录无index.html且demo/index.html不存在，跳过")
                return
            write_file(iuh, base_demo)
            Msg.info("程序首页","程序目录无index.html，已复制demo/index.html生成")
        base_fallback=read_file(iuh)
        if not base_demo and not base_fallback:
            Msg.error("程序首页","无可用模板(demo/index.html或index.html)"); return
        base = base_demo or base_fallback
        mc=read_file(iuall) or ''
        raw_items=[item for item in mc.split('<!-- site_page -->')[1:] if item.strip()]
        all_items=[]; seen=set()
        for item in raw_items:
            item=item.replace('{','').replace('}','')
            um=re.search(r'href="([^"]+)"',item)
            key=um.group(1) if um else item
            if key not in seen:
                seen.add(key); all_items.append(item)
        total=len(all_items)
        page_size=30
        pages=(total+page_size-1)//page_size
        dom_raw=self.dv.get().strip()
        if not dom_raw:
            dom_fp=os.path.join(PROGRAM_DIR,'domain.txt')
            if os.path.exists(dom_fp):
                dl=[l.strip() for l in (read_file(dom_fp) or '').split('\n') if l.strip()]
                dom_raw=dl[0] if dl else ''
        dom_safe=re.sub(r'^https?://','',dom_raw).split('/')[0].strip() if dom_raw else ''
        dom_safe=sfn(dom_safe) or 'localhost'
        uf=os.path.join(PROGRAM_DIR,'url.txt')
        side_links=''
        if os.path.exists(uf):
            uls=[l.strip() for l in (read_file(uf,errors='replace') or '').split('\n')
                 if l.strip() and l.strip().startswith('<a') and '</a>' in l.strip()]
            if uls:
                side_links='\n'.join(random.sample(uls, min(6,len(uls))))
        def fill(base, items_slice, nav_html):
            if not items_slice:
                cards=''
            else:
                cards='\n'.join(items_slice)
            content=re.sub(r'<!-- site_page_begin -->.*?<!-- site_page_end -->',
                           lambda m:f'<!-- site_page_begin -->\n{cards}\n<!-- site_page_end -->',
                           base, flags=re.DOTALL)
            content=re.sub(r'<a href="page_nav_link"[^>]*>.*?</a>', lambda m:nav_html, content, flags=re.DOTALL)
            content=re.sub(r'<!-- page_nav_link-->', lambda m:nav_html, content)
            if side_links:
                content=re.sub(r'<!-- new_link_name_start-->.*?<!-- new_link_name_end-->',
                               lambda m:f'<!-- new_link_name_start-->\n{side_links}\n<!-- new_link_name_end-->',
                               content, flags=re.DOTALL)
            return content
        num_files = pages - 1 if total > page_size else 0
        # 重新生成index.html作为第1页（最新30条），其余页生成{域名}_index_{id}.html
        write_file(iuh, fill(base_demo or base_fallback, all_items[0:page_size], f'<a href="{dom_safe}_index_1.html" aria-label="下一页">下一页</a>' if num_files>0 else ''))
        for pid in range(1, num_files+1):
            prev='index.html' if pid==1 else f'{dom_safe}_index_{pid-1}.html'
            nxt=f'{dom_safe}_index_{pid+1}.html' if pid<num_files else ''
            nav=''
            nav+=f'<a href="{prev}" aria-label="上一页">上一页</a> '
            if nxt: nav+=f'<a href="{nxt}" aria-label="下一页">下一页</a>'
            sl=all_items[pid*page_size:(pid+1)*page_size]
            write_file(os.path.join(PROGRAM_DIR,f'{dom_safe}_index_{pid}.html'), fill(base_demo or base_fallback, sl, nav.strip()))
        pats=re.compile(r'^'+re.escape(dom_safe)+r'_index_([0-9]+)\.html$')
        for f in os.listdir(PROGRAM_DIR):
            m2=pats.match(f)
            if m2 and int(m2.group(1))>num_files:
                try: os.remove(os.path.join(PROGRAM_DIR,f))
                except: pass
        Msg.info("程序首页",f"已生成index.html（最新{min(page_size,total)}条）"+(f"及{num_files}个分页文件" if num_files else "，未超30条不分页"))
    def _add_log(self, icon, msg, level='info'):
        ts=datetime.now().strftime('%H:%M:%S')
        entry=f'[{ts}] {icon} {msg}'
        self.log_entries.append(entry)
        if len(self.log_entries) > 100:
            overflow = self.log_entries[:len(self.log_entries)-100]
            self.log_entries = self.log_entries[-100:]
            lines = [line for line in self.log_t.get('1.0', tk.END).split('\n') if line]
            for line in overflow:
                if line in lines:
                    lines.remove(line)
            self.log_t.delete('1.0', tk.END)
            self.log_t.insert('1.0', '\n'.join(lines) + ('\n' if lines else ''))
        self.log_t.insert(tk.END, entry + '\n')
        self.log_t.see(tk.END)
    def _clear_log(self):
        self.log_entries.clear()
        self.log_t.delete('1.0', tk.END)
    def _copy_log(self):
        content='\n'.join(self.log_entries)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        print('[系统] 日志已复制到剪贴板')
    def _quit(self):
        self.root.destroy()

if __name__=='__main__':
    ensure_dirs()
    root=tk.Tk()
    app=App(root)
    LogPanel.set_panel(app)
    root.mainloop()
