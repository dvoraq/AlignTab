import sublime
import sublime_plugin
import re
from .parser import input_parser
from .wclen import wclen
from .hist import AlignTabHistory
from .table import toogle_table_mode

def get_named_pattern(user_input):
    s = sublime.load_settings('AlignTab.sublime-settings')
    patterns = s.get('named_patterns', {})
    user_input = patterns[user_input] if user_input in patterns else user_input
    user_input = AlignTabHistory.HIST[-1] if AlignTabHistory.HIST and \
                                    user_input == 'last_rexp' else user_input
    return user_input

class Aligner:
    def __init__(self, view, user_input, get_line, replace_line):
        self.view = view
        self.get_line = get_line
        self.replace_line = replace_line
        user_input = get_named_pattern(user_input)
        [regex, self.flag, self.maxs] = input_parser(user_input)
        self.regex = '(' + regex + ')'
        # do not strip \t if translate_tabs_to_spaces is false
        t2s = view.settings().get("translate_tabs_to_spaces", False)
        self.strip_char = ' ' if not t2s else None
        self.colwidth = []
        self.rows = []

    def update_colwidth(self, content):
        thiscolwidth = [wclen(c) for c in content]
        for i,w in enumerate(thiscolwidth):
            if i<len(self.colwidth):
                self.colwidth[i] = max(self.colwidth[i], w)
            else:
                self.colwidth.append(w)

    def fill_spaces(self, content):
        for k in range(len(content)):
            ju = self.flag[k % len(self.flag)]
            align = ju[0]
            pedding = " "*ju[1] if k<len(content)-1 else ""
            fill = self.colwidth[k]-wclen(content[k])
            if align=='l':
                content[k] = content[k] + " "*fill + pedding
            elif align == 'r':
                content[k] = " "*fill + content[k] + pedding
            elif align == 'c':
                lfill = " "*int(fill/2)
                rfill = " "*(fill-int(fill/2))
                content[k] = lfill + content[k] + rfill + pedding

    def line_split(self, row):
        content = [s for s in re.split(self.regex, self.get_line(row), self.maxs)]
        # remove indentation
        if len(content)>1:
            content[0] = content[0].lstrip()
        # remove spaces
        content = [c.strip(self.strip_char) for c in content]
        return content

    def expand_sel(self):
        view = self.view
        lastrow = view.rowcol(view.size())[0]

        for sel in view.sel():
            for line in view.lines(sel):
                thisrow = view.rowcol(line.begin())[0]
                if (thisrow in self.rows): continue
                content = self.line_split(thisrow)
                if len(content)<=1: continue
                self.update_colwidth(content)
                self.rows.append(thisrow)

            if sel.empty():
                thisrow = view.rowcol(sel.begin())[0]
                if not (thisrow in self.rows): continue
                beginrow = endrow = thisrow
                while endrow+1<=lastrow and not (endrow+1 in self.rows):
                    content = self.line_split(endrow+1)
                    if len(content)<=1: break
                    self.update_colwidth(content)
                    endrow = endrow+1
                    self.rows.append(endrow)
                while beginrow-1>=0 and not (beginrow-1 in self.rows):
                    content = self.line_split(beginrow-1)
                    if len(content)<=1: break
                    self.update_colwidth(content)
                    beginrow = beginrow-1
                    self.rows.append(beginrow)

    def align(self):
        indentation = min([re.match("^(\s*)", self.get_line(row)).group(1)
                            for row in self.rows])
        for row in reversed(self.rows):
            content = self.line_split(row)
            self.fill_spaces(content)
            content = (indentation + "".join(content).rstrip(self.strip_char))
            self.replace_line(row, content)



class AlignTabCommand(sublime_plugin.TextCommand):
    def run(self, edit, user_input=None, mode=False, live_preview=False):
        view = self.view
        vid = view.id()
        if not user_input:
            self.aligned = False
            v = self.view.window().show_input_panel('Align By RegEx:', '',
                    # On Done
                    lambda x: self.on_done(x, mode, live_preview),
                    # On Change
                    lambda x: self.on_change(x) if live_preview else None,
                    # On Cancel
                    lambda: self.on_change(None) if live_preview else None )
            v.set_syntax_file('Packages/AlignTab/AlignTab.hidden-tmLanguage')
            v.settings().set('is_widget', True)
            v.settings().set('gutter', False)
            v.settings().set('rulers', [])

        elif user_input:
            def get_line(row):
                return view.substr(view.line(view.text_point(row,0)))

            def replace_line(row, content):
                line = view.line(view.text_point(row,0))
                view.replace(edit, line, content)

            aligner = Aligner(view, user_input, get_line, replace_line)
            aligner.expand_sel()

            try:
                True
            except:
                self.aligned = False
                return
            if aligner.rows:
                self.aligned = True
                aligner.align()
                if mode:
                    toogle_table_mode(vid, True)
                else:
                    sublime.status_message("")
            else:
                self.aligned = False
                if mode and not all(list(self.prev_next_match())):
                    toogle_table_mode(vid, False)
                else:
                    sublime.status_message("[Pattern not Found]")


    def on_change(self, user_input):
        view = self.view
        vid = view.id()
        # Undo the previous change if needed
        if self.aligned:
            self.view.run_command("soft_undo")
            self.aligned = False
        if user_input:
            self.view.run_command("align_tab",
                {"user_input":user_input, "live_preview":True})

    def on_done(self, user_input, mode, live_preview):
        view = self.view
        AlignTabHistory.insert(user_input)
        # do not double align when done with live preview mode
        if not live_preview:
            self.view.run_command("align_tab",
                {"user_input":user_input, "mode":mode})


    # def align_tab(self, edit, mode):
    #     [regex, flag, maxs, strip_char] = self.opt
    #     view = self.view
    #     vid  = view.id()

    #     # test validity of regex
    #     try:
    #         re.compile(regex)
    #     except:
    #         self.aligned = False
    #         return

    #     rows = []
    #     colwidth = []
    #     self.expand_sel(rows, colwidth)
    #     rows = sorted(set(rows))
    #     if rows:
    #         self.aligned = True
    #     else:
    #         self.aligned = False
    #         return

    #     indentation = min([re.match("^(\s*)", self.get_line(row)).group(1)
    #                         for row in rows])

    #     # for table mode, we need to reset the cursor positions
    #     # cursor_rows = set([view.rowcol(s.end())[0] for s in view.sel() if s.empty])
    #     for row in reversed(rows):
    #         line = view.line(view.text_point(row,0))

    #         # if mode and row in cursor_rows:
    #         #     # if this row contains cursors, then need to reset cursor
    #         #     # positions in a complicated way
    #         #     oldcell = self.get_span(row)
    #         #     cursor = [view.rowcol(s.end())[1] for s in view.sel()\
    #         #                          if s.empty and view.rowcol(s.end())[0]==row]

    #         content = self.line_split(row)
    #         fill_spaces(content, colwidth, flag)
    #         view.replace(edit, line,
    #             (indentation + "".join(content).rstrip(strip_char)))

    #         # if mode and row in cursor_rows:
    #         #     newcell = self.get_span(row)
    #         #     for s in view.sel():
    #         #         if s.empty and view.rowcol(s.end())[0]==row: view.sel().subtract(s)
    #         #     for cur in cursor:
    #         #         for i, c in reversed(list(enumerate(oldcell))):
    #         #             if c[0]<= cur:
    #         #                 if cur<=c[1]:
    #         #                     newcur = cur-c[0]+newcell[i][0]
    #         #                 else:
    #         #                     newcur = c[1]-c[0]+newcell[i][0]
    #         #                 break
    #         #         pt = view.text_point(row,newcur)
    #         #         view.sel().add(sublime.Region(pt,pt))

    # def get_span(self, row):
    #     # it is used to reset cursor for table mode
    #     [regex, flag, maxs, strip_char] = self.opt
    #     view = self.view
    #     line = self.get_line(row)
    #     p = [m.span() for m in re.finditer(regex, line)]
    #     if maxs>0: p = p[0:maxs]
    #     p += [(wclen(line),None)]
    #     cell = []
    #     for i in range(len(p)-1):
    #         cell += [p[i],(p[i][1],p[i+1][0])]
    #     cell = [(0,p[0][0])] + cell
    #     for i,c in enumerate(cell):
    #         cellcontent = line[c[0]:c[1]]
    #         b = cell[i][1]-wclen(cellcontent)+wclen(cellcontent.rstrip(strip_char))
    #         a = b - wclen(cellcontent.strip(strip_char))
    #         cell[i] = (a, b)
    #     return cell


    # def prev_next_match(self):
    #     # it is used to check whether table mode should be disabled
    #     view = self.view
    #     lastrow = view.rowcol(view.size())[0]
    #     rows = []
    #     for sel in view.sel():
    #         for line in view.lines(sel):
    #             rows.append(view.rowcol(line.begin())[0])
    #     rows = list(set(rows))
    #     for row in rows:
    #         if row-1>=0 and len(self.line_split(row-1))>1:
    #             yield True
    #         elif row+1<=lastrow and len(self.line_split(row+1))>1:
    #             yield True
    #         else:
    #             yield False
