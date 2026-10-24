// .NET Framework 4.x; no injection, elevation or changes to cursor registry settings.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

internal enum Edge { None = -1, N, NE, E, SE, S, SW, W, NW }

internal static class Native
{
    internal const uint ImageCursor = 2;
    internal static readonly int CursorInfoSize = Marshal.SizeOf(typeof(CursorInfo));
    internal static readonly uint[] Roles = { 32642, 32643, 32644, 32645 };

    [StructLayout(LayoutKind.Sequential)]
    internal struct Point { internal int X, Y; }
    [StructLayout(LayoutKind.Sequential)]
    internal struct CursorInfo { internal int Size, Flags; internal IntPtr Cursor; internal Point Position; }
    [StructLayout(LayoutKind.Sequential)]
    internal struct IconInfo { internal int Icon; internal uint HotX, HotY; internal IntPtr Mask, Color; }
    [StructLayout(LayoutKind.Sequential)]
    internal struct BitmapInfo
    {
        internal int Type, Width, Height, WidthBytes;
        internal ushort Planes, BitsPixel;
        internal IntPtr Bits;
    }

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern IntPtr LoadCursorW(IntPtr instance, IntPtr name);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern IntPtr LoadImageW(IntPtr instance, string name, uint type, int width, int height, uint flags);
    [DllImport("user32.dll", SetLastError = true)]
    internal static extern IntPtr CopyImage(IntPtr image, uint type, int width, int height, uint flags);
    [DllImport("user32.dll", SetLastError = true)]
    internal static extern bool SetSystemCursor(IntPtr cursor, uint role);
    [DllImport("user32.dll", SetLastError = true)]
    internal static extern bool DestroyCursor(IntPtr cursor);
    [DllImport("user32.dll", SetLastError = true)]
    internal static extern bool GetCursorInfo(ref CursorInfo info);
    [DllImport("user32.dll")]
    internal static extern IntPtr WindowFromPoint(Point point);
    [DllImport("user32.dll")]
    internal static extern IntPtr GetAncestor(IntPtr window, uint flags);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern IntPtr SendMessageTimeoutW(IntPtr window, uint message, UIntPtr wParam,
        IntPtr lParam, uint flags, uint timeout, out UIntPtr result);
    [DllImport("user32.dll")]
    internal static extern short GetAsyncKeyState(int key);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    internal static extern bool SystemParametersInfoW(uint action, uint parameter, IntPtr value, uint flags);
    [DllImport("user32.dll")]
    private static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")]
    private static extern bool SetProcessDPIAware();
    [DllImport("user32.dll", SetLastError = true)]
    internal static extern bool GetIconInfo(IntPtr cursor, out IconInfo info);
    [DllImport("gdi32.dll", EntryPoint = "GetObjectW", SetLastError = true)]
    private static extern int GetObject(IntPtr image, int size, out BitmapInfo info);
    [DllImport("gdi32.dll")]
    internal static extern bool DeleteObject(IntPtr image);

    internal static void DpiAware()
    {
        try { SetProcessDpiAwarenessContext(new IntPtr(-4)); }
        catch (EntryPointNotFoundException) { SetProcessDPIAware(); }
    }

    internal static void Check(bool ok) { if (!ok) throw new Win32Exception(Marshal.GetLastWin32Error()); }
    internal static IntPtr Cursor(uint role)
    {
        IntPtr cursor = LoadCursorW(IntPtr.Zero, new IntPtr(role));
        Check(cursor != IntPtr.Zero);
        return cursor;
    }
    internal static uint ActiveRole(IntPtr cursor)
    {
        foreach (uint role in Roles)
            if (cursor == Cursor(role)) return role;
        return 0;
    }
    internal static IntPtr LoadHook(string directory, Edge edge, Size size)
    {
        string file = Path.Combine(directory, "resize-" + edge.ToString().ToLowerInvariant() + ".cur");
        IntPtr cursor = LoadImageW(IntPtr.Zero, file, ImageCursor, size.Width, size.Height, 0x0010);
        Check(cursor != IntPtr.Zero); // LR_LOADFROMFILE, no LR_SHARED.
        return cursor;
    }
    internal static IntPtr Copy(IntPtr cursor)
    {
        IntPtr copy = CopyImage(cursor, ImageCursor, 0, 0, 0); // Always a new, owned handle.
        Check(copy != IntPtr.Zero);
        return copy;
    }
    internal static void Replace(uint role, IntPtr cursor)
    {
        IntPtr copy = Copy(cursor); // SetSystemCursor consumes this copy, never the cached original.
        if (SetSystemCursor(copy, role)) return;
        int error = Marshal.GetLastWin32Error();
        DestroyCursor(copy);
        throw new Win32Exception(error);
    }
    internal static Size CursorSize(IntPtr cursor)
    {
        IconInfo icon;
        Check(GetIconInfo(cursor, out icon));
        try
        {
            BitmapInfo bitmap;
            Check(GetObject(icon.Color != IntPtr.Zero ? icon.Color : icon.Mask,
                Marshal.SizeOf(typeof(BitmapInfo)), out bitmap) != 0);
            return new Size(bitmap.Width, icon.Color != IntPtr.Zero ? bitmap.Height : bitmap.Height / 2);
        }
        finally
        {
            if (icon.Color != IntPtr.Zero) DeleteObject(icon.Color);
            if (icon.Mask != IntPtr.Zero) DeleteObject(icon.Mask);
        }
    }
    internal static Edge FromHit(int hit)
    {
        switch (hit)
        {
            case 10: return Edge.W;
            case 11: return Edge.E;
            case 12: return Edge.N;
            case 13: return Edge.NW;
            case 14: return Edge.NE;
            case 15: return Edge.S;
            case 16: return Edge.SW;
            case 17: case 4: return Edge.SE;
            default: return Edge.None;
        }
    }
    internal static uint Role(Edge edge)
    {
        switch (edge)
        {
            case Edge.NW: case Edge.SE: return 32642;
            case Edge.NE: case Edge.SW: return 32643;
            case Edge.W: case Edge.E: return 32644;
            case Edge.N: case Edge.S: return 32645;
            default: return 0;
        }
    }
    internal static IntPtr Packed(Point point)
    {
        return new IntPtr(unchecked((point.X & 0xffff) | ((point.Y & 0xffff) << 16)));
    }
    internal static Edge HitTest(Point point)
    {
        // WM_NCHITTEST packs signed 16-bit screen coordinates.
        if (point.X < short.MinValue || point.X > short.MaxValue ||
            point.Y < short.MinValue || point.Y > short.MaxValue) return Edge.None;
        IntPtr window = WindowFromPoint(point);
        if (window == IntPtr.Zero) return Edge.None;
        window = GetAncestor(window, 2); // GA_ROOT
        if (window == IntPtr.Zero) return Edge.None;
        UIntPtr hit;
        // WM_NCHITTEST; BLOCK | ABORTIFHUNG | ERRORONEXIT, capped at 20 ms.
        if (SendMessageTimeoutW(window, 0x0084, UIntPtr.Zero, Packed(point), 0x23, 20, out hit) == IntPtr.Zero)
            return Edge.None;
        return FromHit(unchecked((int)hit.ToUInt64()));
    }
    internal static void Reload() { Check(SystemParametersInfoW(0x0057, 0, IntPtr.Zero, 0)); }
}

internal sealed class SettingsWatch : IDisposable
{
    private readonly RegistryKey key = Registry.CurrentUser.OpenSubKey(@"Control Panel\Cursors");
    private readonly EventWaitHandle changed = new EventWaitHandle(false, EventResetMode.AutoReset);
    [DllImport("advapi32.dll")]
    private static extern int RegNotifyChangeKeyValue(Microsoft.Win32.SafeHandles.SafeRegistryHandle key,
        bool subtree, uint filter, IntPtr signal, bool async);
    internal SettingsWatch() { Arm(); }
    private void Arm()
    {
        int error = RegNotifyChangeKeyValue(key.Handle, false, 4, changed.SafeWaitHandle.DangerousGetHandle(), true);
        if (error != 0) throw new Win32Exception(error); // REG_NOTIFY_CHANGE_LAST_SET
    }
    internal bool Poll()
    {
        if (!changed.WaitOne(0)) return false;
        Arm();
        return true;
    }
    public void Dispose() { key.Dispose(); changed.Dispose(); }
}

internal sealed class ResizeContext : ApplicationContext
{
    internal const string StopName = "Local\\OnePiece.DirectionalResize.Stop";
    private readonly Dictionary<uint, IntPtr> originals = new Dictionary<uint, IntPtr>();
    private readonly Dictionary<Edge, IntPtr> hooks = new Dictionary<Edge, IntPtr>();
    private readonly Dictionary<uint, Edge> applied = new Dictionary<uint, Edge>();
    private readonly Dictionary<string, string> settings = new Dictionary<string, string>();
    private readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
    private readonly EventWaitHandle stop = new EventWaitHandle(false, EventResetMode.AutoReset, StopName);
    private readonly SettingsWatch settingsWatch = new SettingsWatch();
    private readonly NotifyIcon tray = new NotifyIcon();
    private readonly ToolStripMenuItem pause = new ToolStripMenuItem("Pause");
    private bool enabled, held, paused;
    private Edge hovered = Edge.None, dragging = Edge.None;
    private readonly string directory;
    private static readonly string[] SettingNames = { "SizeNWSE", "SizeNESW", "SizeWE", "SizeNS" };

    internal ResizeContext(string directory)
    {
        this.directory = directory;
        try
        {
            CaptureSettings();
            LoadCursors();
            var menu = new ContextMenuStrip();
            pause.Click += delegate { Toggle(); };
            menu.Items.Add(pause);
            menu.Items.Add("Restore current scheme", null, delegate { paused = true; RestoreScheme(); });
            menu.Items.Add("Exit — restore cursors", null, delegate { ExitThread(); });
            tray.Icon = SystemIcons.Application;
            tray.Text = "One Piece: eight-direction resize";
            tray.ContextMenuStrip = menu;
            tray.Visible = true;
            SetEnabled(SameScheme()); // Login startup must not replace another theme's resize cursors.
            timer.Interval = 100;
            timer.Tick += delegate { Tick(); };
            timer.Start();
        }
        catch { Dispose(); throw; }
    }
    private void LoadCursors()
    {
        foreach (uint role in Native.Roles) originals[role] = Native.Copy(Native.Cursor(role));
        foreach (Edge edge in Enum.GetValues(typeof(Edge)))
        {
            if (edge == Edge.None) continue;
            Size size = Native.CursorSize(originals[Native.Role(edge)]);
            hooks[edge] = Native.LoadHook(directory, edge, size);
        }
    }
    private void FreeCursors()
    {
        foreach (IntPtr cursor in originals.Values) Native.DestroyCursor(cursor);
        foreach (IntPtr cursor in hooks.Values) Native.DestroyCursor(cursor);
        originals.Clear();
        hooks.Clear();
    }
    private void CaptureSettings()
    {
        using (RegistryKey key = Registry.CurrentUser.OpenSubKey(@"Control Panel\Cursors"))
            foreach (string name in SettingNames) settings[name] = Convert.ToString(key.GetValue(name));
    }
    private bool SameScheme()
    {
        using (RegistryKey key = Registry.CurrentUser.OpenSubKey(@"Control Panel\Cursors"))
            foreach (string name in SettingNames)
            {
                string path = Convert.ToString(key.GetValue(name));
                if (!String.Equals(settings[name], path, StringComparison.OrdinalIgnoreCase) ||
                    String.IsNullOrEmpty(path) ||
                    !String.Equals(Path.GetFileName(Path.GetDirectoryName(path)), "OnePiece", StringComparison.OrdinalIgnoreCase))
                    return false;
            }
        return true;
    }
    private void SetEnabled(bool value)
    {
        enabled = value;
        pause.Text = value ? "Pause" : "Resume";
    }
    private void ClearState()
    {
        applied.Clear();
        hovered = dragging = Edge.None;
    }
    private void ResetCursors()
    {
        Native.Reload();
        ClearState();
        FreeCursors();
        CaptureSettings();
        LoadCursors();
    }
    private void RestoreScheme()
    {
        Native.Reload();
        ClearState();
        SetEnabled(false);
    }
    private void Restore()
    {
        if (applied.Count != 0 && !SameScheme()) { RestoreScheme(); return; }
        foreach (var cursor in applied) Native.Replace(cursor.Key, originals[cursor.Key]);
        ClearState();
    }
    private void Toggle()
    {
        if (enabled) { Restore(); paused = true; SetEnabled(false); return; }
        if (!SameScheme()) { MessageBox.Show("Select your One Piece cursor scheme before resuming."); return; }
        paused = false;
        ResetCursors();
        SetEnabled(true);
    }
    private void UpdateDrag(bool down)
    {
        if (!down) dragging = Edge.None;
        else if (!held) dragging = hovered;
        held = down;
    }
    private void Apply(uint role, Edge edge)
    {
        Edge previous;
        if (applied.TryGetValue(role, out previous) && previous == edge) return;
        Native.Replace(role, hooks[edge]);
        applied[role] = edge;
    }
    private void UpdateCursor()
    {
        Native.CursorInfo info = new Native.CursorInfo { Size = Native.CursorInfoSize };
        if (!Native.GetCursorInfo(ref info) || (info.Flags & 1) == 0) { Restore(); return; }
        uint active = Native.ActiveRole(info.Cursor);
        bool down = Native.GetAsyncKeyState(1) < 0 || Native.GetAsyncKeyState(2) < 0;
        UpdateDrag(down);
        if (active == 0) { timer.Interval = 100; Restore(); return; }
        timer.Interval = 30;
        Edge edge = down && dragging != Edge.None ? dragging : Native.HitTest(info.Position);
        if (Native.Role(edge) != active) { Restore(); return; } // Don't guess for client-area splitters.
        hovered = edge;
        if (down && dragging == Edge.None) dragging = edge;
        Apply(active, edge);
    }
    private void Tick()
    {
        try
        {
            if (stop.WaitOne(0)) { ExitThread(); return; }
            if (settingsWatch.Poll())
            {
                ResetCursors(); // Registry edits only, never our own cursor swaps.
                SetEnabled(!paused && SameScheme());
            }
            if (!enabled) { timer.Interval = 150; return; }
            UpdateCursor();
        }
        catch (Exception error)
        {
            paused = true;
            SetEnabled(false);
            Native.SystemParametersInfoW(0x0057, 0, IntPtr.Zero, 0);
            ClearState();
            tray.ShowBalloonTip(5000, "Directional resize paused", error.Message, ToolTipIcon.Warning);
        }
    }
    protected override void Dispose(bool disposing)
    {
        if (!disposing) { base.Dispose(false); return; }
        timer.Stop();
        timer.Dispose();
        if (applied.Count != 0) Native.SystemParametersInfoW(0x0057, 0, IntPtr.Zero, 0);
        FreeCursors();
        tray.Visible = false;
        if (tray.ContextMenuStrip != null) tray.ContextMenuStrip.Dispose();
        tray.Dispose();
        settingsWatch.Dispose();
        stop.Dispose();
        base.Dispose(true);
    }
}

internal static class Program
{
    private static string Signature(IntPtr cursor)
    {
        Native.IconInfo icon;
        Native.Check(Native.GetIconInfo(cursor, out icon));
        try
        {
            using (Image image = Image.FromHbitmap(icon.Color != IntPtr.Zero ? icon.Color : icon.Mask))
            using (var bytes = new MemoryStream())
            {
                image.Save(bytes, System.Drawing.Imaging.ImageFormat.Png);
                return icon.HotX + "," + icon.HotY + ":" + Convert.ToBase64String(bytes.ToArray());
            }
        }
        finally
        {
            if (icon.Color != IntPtr.Zero) Native.DeleteObject(icon.Color);
            if (icon.Mask != IntPtr.Zero) Native.DeleteObject(icon.Mask);
        }
    }
    private static void CheckEdges(string directory)
    {
        int[] hits = { 12, 14, 11, 17, 15, 16, 10, 13 };
        for (int i = 0; i < hits.Length; i++)
        {
            Edge edge = (Edge)i;
            if (Native.FromHit(hits[i]) != edge || Native.Role(edge) == 0) throw new Exception("Invalid edge mapping.");
            IntPtr cursor = Native.LoadHook(directory, edge, new Size(32, 32));
            try { if (Native.CursorSize(cursor) != new Size(32, 32)) throw new Exception("Invalid cursor dimensions."); }
            finally { Native.DestroyCursor(cursor); }
        }
        if (Native.FromHit(1) != Edge.None) throw new Exception("Client areas must remain untouched.");
    }
    private static void CheckCoordinates()
    {
        long packed = Native.Packed(new Native.Point { X = -1200, Y = -200 }).ToInt64();
        if ((short)(packed & 0xffff) != -1200 || (short)((packed >> 16) & 0xffff) != -200)
            throw new Exception("Negative screen coordinates are invalid.");
    }
    private static void CheckReplacements(string directory)
    {
        // Exercise all eight replacements, pixel identity, stable handles and restoration.
        var originals = new Dictionary<uint, IntPtr>();
        try
        {
            foreach (uint role in Native.Roles) originals[role] = Native.Copy(Native.Cursor(role));
            foreach (Edge edge in Enum.GetValues(typeof(Edge)))
            {
                if (edge == Edge.None) continue;
                uint role = Native.Role(edge);
                IntPtr shared = Native.Cursor(role);
                Size size = Native.CursorSize(originals[role]);
                IntPtr cursor = Native.LoadHook(directory, edge, size);
                try
                {
                    Native.Replace(role, cursor);
                    if (Native.Cursor(role) != shared || Signature(shared) != Signature(cursor))
                        throw new Exception("Directional cursor replacement failed.");
                }
                finally { Native.DestroyCursor(cursor); }
            }
        }
        finally
        {
            foreach (var original in originals)
            {
                try { Native.Replace(original.Key, original.Value); }
                finally { Native.DestroyCursor(original.Value); }
            }
        }
    }
    private static void SelfTest(string directory)
    {
        CheckEdges(directory);
        CheckCoordinates();
        using (var watcher = new SettingsWatch()) watcher.Poll();
        CheckReplacements(directory);
    }
    private static void Run(string directory)
    {
        bool created;
        using (var single = new Mutex(true, "Local\\OnePiece.DirectionalResize", out created))
        {
            if (!created) return;
            try
            {
                Application.SetUnhandledExceptionMode(UnhandledExceptionMode.ThrowException);
                Application.EnableVisualStyles();
                using (var context = new ResizeContext(directory)) Application.Run(context);
            }
            finally { single.ReleaseMutex(); }
        }
    }
    [STAThread]
    private static int Main(string[] args)
    {
        bool testing = args.Length > 0 && args[0] == "--self-test";
        try
        {
            Native.DpiAware();
            string directory = AppDomain.CurrentDomain.BaseDirectory;
            if (args.Length > 0 && args[0] == "--restore") { Native.Reload(); return 0; }
            if (testing) { SelfTest(directory); return 0; }
            Run(directory);
            return 0;
        }
        catch (Exception error)
        {
            if (!testing) MessageBox.Show(error.Message, "One Piece directional resize", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
