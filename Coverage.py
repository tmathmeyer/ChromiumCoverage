


import sublime_plugin
import sublime
import os


SETTINGS = "Coverage.sublime-settings"


def skip(count, iterable):
  def __iterate():
    yield from iterable
  iterator = __iterate()
  for i in range(count):
    next(iterator)
  yield from iterator


class CoverageCommand(sublime_plugin.WindowCommand):
  def RequestInputSeries(self, cb, input_map, collect=None):
    collect = collect or {}
    def bind(key, rest):
      def bound(value):
        collect[key] = value
        self.RequestInputSeries(cb, rest, collect)
      return bound
    if input_map:
      first, *rest = input_map
      key, label = first
      self.window.show_input_panel(label, "", bind(key, list(rest)), None, None)
      return
    cb(**collect)

  def FormatTarget(self, t):
    return '{} --gtest_filter="{}"'.format(t["target"], t["filter"])

  def GetCoverageMetadataFromView(self, view):
    settings = sublime.load_settings(SETTINGS)
    working_dir = settings.get("chromium_checkout")
    chromium_outdir = settings.get("chromium_build_dir")
    file_path = view.file_name()
    if not file_path:
      return None
    if not file_path.startswith(working_dir):
      return None
    _, remainder = file_path.split(working_dir)
    return '{}/out/{}/report/text/coverage{}.txt'.format(
      working_dir, chromium_outdir, remainder)

  def RenderCoverageViews(self, views):
    for view in views:
      coverage_output_file = self.GetCoverageMetadataFromView(view)
      if coverage_output_file:
        covered_regions = []
        uncovered_regions = []
        active_region_start = None
        active_region_covered = ""
        view.erase_regions("covered")
        view.erase_regions("uncovered")
        if os.path.exists(coverage_output_file):
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
          view.add_regions("covered", covered_regions, "region.greenish")
          view.add_regions("uncovered", uncovered_regions, "region.redish")

  def CreateNewCoverageTarget(self, cb):
    def SaveCoverageTarget(target, filter):
      settings = sublime.load_settings(SETTINGS)
      targets = settings.get("targets", [])
      targets.append({
        "target": target,
        "filter": filter,
      })
      settings.set("targets", targets)
      sublime.save_settings(SETTINGS)
      cb(target, filter)
    self.RequestInputSeries(SaveCoverageTarget, [
      ("target", "Unit Test Target"),
      ("filter", "Gtest Filter"),
    ])

  def GetCoverageTargetRunner(self, views):
    def CoverageTargetRunner(target, filter):
      settings = sublime.load_settings(SETTINGS)
      working_dir = settings.get("chromium_checkout")
      chromium_outdir = settings.get("chromium_build_dir")
      script_dir = settings.get("coverage_script_dir")
      depot_tools_dir = settings.get("depot_tools_dir")
      sources = []
      for view in views:
        viewfile = view.file_name()
        if viewfile and viewfile.startswith(working_dir):
          sources.append(viewfile[len(working_dir)+1:])
      source_string = ' '.join(sources)
      env = os.environ.copy()
      env["PATH"] = os.pathsep.join([
        script_dir, depot_tools_dir, env.get("PATH", "")
      ])
      command = "git coverage script {} \"{}\" {}"
      formatted = command.format(target, filter, source_string)
      print(formatted)
      self.window.run_command("exec", {
        "shell_cmd": formatted,
        "env": env,
        "working_dir": working_dir,
        "encoding": "utf-8",
      })
    return CoverageTargetRunner

  def GetInstrumentedTestTarget(self, cb):
    settings = sublime.load_settings(SETTINGS)
    targets = settings.get("targets") or []
    items = ["Create New Target"]
    items += [FormatTarget(t) for t in targets[::-1]]
    def InterceptTarget(index):
      if index < 0:
        return
      if index == 0:
        self.CreateNewCoverageTarget(cb)
        return
      cb(**targets[::-1][index-1])
    self.window.show_quick_panel(items, InterceptTarget)



class CvCoverageCurrentFile(CoverageCommand):
  def run(self, *args, **kwargs):
    view = sublime.active_window().active_view()
    self.GetInstrumentedTestTarget(self.GetCoverageTargetRunner([view]))


class CvCoverageOpenFiles(CoverageCommand):
  def run(self, *args, **kwargs):
    views = sublime.active_window().views()
    self.GetInstrumentedTestTarget(self.GetCoverageTargetRunner(views))


class CvCoverageRenderCurrentFile(CoverageCommand):
  def run(self, *args, **kwargs):
    view = sublime.active_window().active_view()
    self.RenderCoverageViews([view])


class CvCoverageRenderOpenFiles(CoverageCommand):
  def run(self, *args, **kwargs):
    views = sublime.active_window().views()
    self.RenderCoverageViews(views)
