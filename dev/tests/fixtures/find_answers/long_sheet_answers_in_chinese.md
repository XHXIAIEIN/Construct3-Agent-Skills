事件 103 处理终点线，游戏在事件 108 重新开始。事件号是编辑器边栏显示的号码。

**冲过终点线（事件 102–105，组 "Finish Line"）**

1. 事件 103 `TractorBase: On collision with FinishLine` 调用 `prepareForGameOver()`（事件 107）。该函数停止计时器，把 `movementChecking` 设为 False，停止 UFO，把车的最大速度清零，停止 AI，并隐藏红绿灯和仪表。
2. 事件 104 是玩家拖拉机的子事件（`TractorBase: Pick Own children Player`），调用 `showGameOver("success")`。
3. 事件 105 是 `System: Else` 的子事件，调用 `showGameOver("fail")`，即 AI 拖拉机越过终点线时。

**游戏在哪里重新开始（事件 108，`function showGameOver(type: string)`）**

事件 108 显示 FAIL 或 SUCCESS 文字，淡入 Fader 和结束文字，然后等待 4 秒。接着隐藏文字，执行 `System: Restart layout`，再执行 `System: Reset global variables to default`。全表只有这一处 `Restart layout`，所在表运行于 Game 布局。

事件 108 还有另一条入口：事件 88（Movement Checker 组）在玩家拥有的拖拉机被 AI 移动时调用 `prepareForGameOver()`；事件 91 在 `Player.Count` 降为 0 时调用 `showGameOver("fail")`。

检查器通过（最后一行为 `ok:`），其警告针对已弃用的表达式和省略的参数，与终点和重开逻辑无关。未运行编辑器或预览，结论来自读取事件表。

来源：子 agent 的读取结果，记录在 commands.txt 中。事件号未在编辑器中核对。
