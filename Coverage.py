


import sublime_plugin
import sublime
import os


SETTINGS = "Coverage.sublime-settings"



class CoverageCommand(sublime_plugin.WindowCommand):
  @staticmethod
  def RequestInputSeries(self, cb, input_map, collect=None):
    collect = collect or {}
    def bind(key, rest):
      def bound(value):
        collect[key] = value
        self.RequestInputSeries(window, cb, rest, collect)
      return bound
    if input_map:
      first, *rest = input_map
      key, label = first
      self.window.show_input_panel(label, "", bind(key, list(rest)), None, None)
      return
    cb(**collect)

def _RequestInputSeries(window, cb, input_map, collect=None):
  collect = collect or {}
  def bind(key, rest):
    def bound(value):
      collect[key] = value
      _RequestInputSeries(window, cb, rest, collect)
    return bound

  if input_map:
    first, *rest = input_map
    key, label = first
    window.show_input_panel(label, "", bind(key, list(rest)), None, None)
    return
  cb(**collect)


def FormatTarget(t):
  filter = t["filter"]
  target = t["target"]
  return target + " --gtest_filter=\"" + filter + "\""


def skip(count, iterable):
  def __iterate():
    yield from iterable
  iterator = __iterate()
  for i in range(count):
    next(iterator)
  yield from iterator


def RenderCoverage(coverage_output_file, view):
  coverage_output_file = '/chromium/src/out/Release/report/text/coverage/media/formats/hls/items.cc.txt'
  covered_regions = []
  uncovered_regions = []
  active_region_start = None
  active_region_covered = ""
  with open(coverage_output_file, "r") as f:
    for line in skip(3, f.readlines()):
      if line.strip():
        line, hits, *_ = line.split("|")
        line_number = int(line.strip())
        hits = hits.strip()
        if hits == "0":
          uncovered_regions.append(view.line(view.text_point(line_number-1, 0)))
        elif hits:
          covered_regions.append(view.line(view.text_point(line_number-1, 0)))
  return covered_regions, uncovered_regions





class CvCoverageCurrentFile(sublime_plugin.WindowCommand):
  def CreateNewCoverageTarget(self):
    _RequestInputSeries(self.window, self.OnNewCoverageTarget, [
      ("target", "Unit Test Target"),
      ("filter", "GTest Filter"),
    ])

  def OnNewCoverageTarget(self, target, filter):
    settings = sublime.load_settings(SETTINGS)
    targets = settings.get("targets", [])
    targets.append({
      "target": target,
      "filter": filter,
    })
    settings.set("targets", targets)
    sublime.save_settings(SETTINGS)
    self.GetInstrumentedTestTarget(self.RunTestTarget)

  def GetInstrumentedTestTarget(self, cb):
    settings = sublime.load_settings(SETTINGS)
    targets = settings.get("targets") or []
    items = ["Create New Target"]
    items += [FormatTarget(t) for t in targets[::-1]]
    def InterceptTarget(index):
      if index < 0:
        return
      if index == 0:
        self.CreateNewCoverageTarget()
        return
      cb(targets[::-1][index-1])
    self.window.show_quick_panel(items, InterceptTarget)

  def RunTestTarget(self, srcfiles):
    def RunTestCb(target_filter, **kwargs):
      settings = sublime.load_settings(SETTINGS)
      working_dir = settings.get("chromium_checkout")
      chromium_outdir = settings.get("chromium_build_dir")
      script_dir = settings.get("coverage_script_dir")
      depot_tools_dir = settings.get("depot_tools_dir")
      srcfiles = ' '.join(srcfiles)
      env = os.environ.copy()
      target = target_filter["target"]
      filter = target_filter["filter"]
      env["PATH"] = os.pathsep.join([
        script_dir, depot_tools_dir, env.get("PATH", "")
      ])
      command = "git coverage script {} {} {}"
      self.window.run_command("exec", {
        "shell_cmd": command.format(target, filter, srcfiles),
        "env": env,
        "working_dir": working_dir,
        "encoding": "utf-8",
      })

      print('{}/out/{}/report/html/coverage'.format(chromium_checkout, chromium_outdir))
    return RunTestCb


  def run(self, **kwargs):
    #settings = sublime.load_settings("Coverage.sublime-settings")
    #checkout = settings["chromium_checkout"]

    '''
    view = self.window.active_view()
    if not view:
      return

    point = view.text_point(8, 0)
    line_region = view.line(point)

    view.add_regions("highlighted_line", [line_region], "region.redish")

    print(kwargs)
    '''

    #os.system("git coverage")
    '''
    self.GetInstrumentedTestTarget(self.RunTestTarget([
      "media/formats/hls/items.cc"
    ]))
    '''
    view = self.window.active_view()
    covered, uncovered = RenderCoverage('', view)
    view.erase_regions("covered")
    view.erase_regions("uncovered")
    view.add_regions("covered", covered, "region.greenish")
    view.add_regions("uncovered", uncovered, "region.redish")
