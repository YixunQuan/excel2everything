
Attribute VB_Name = "DataForgeMacros"
' ============================================
' DataForge Excel 模板 VBA 宏模块
' 功能：根据目录生成表工作表、添加来源表
' ============================================

' 颜色常量
Private Const COLOR_BLUE As Long = 4698580      ' RGB(68, 114, 196)
Private Const COLOR_GREEN As Long = 5287936     ' RGB(70, 173, 71)
Private Const COLOR_ORANGE As Long = 15527148   ' RGB(237, 125, 49)
Private Const COLOR_PURPLE As Long = 7358532    ' RGB(112, 48, 160)
Private Const COLOR_YELLOW As Long = 13421619   ' RGB(255, 217, 102)

' ============================================
' 主功能1：根据目录生成所有表工作表
' ============================================
Sub GenerateTableSheets()
    Dim wsCatalog As Worksheet
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim cnName As String
    Dim enName As String
    Dim sourceCount As Long
    Dim createdCount As Long
    Dim btn As Button
    
    Set wsCatalog = ThisWorkbook.Sheets("目录")
    lastRow = wsCatalog.Cells(wsCatalog.Rows.Count, "B").End(xlUp).Row
    createdCount = 0
    
    Application.ScreenUpdating = False
    
    ' 遍历目录中的表
    For i = 9 To lastRow
        cnName = Trim(wsCatalog.Cells(i, 2).Value)
        enName = Trim(wsCatalog.Cells(i, 3).Value)
        
        ' 跳过空行
        If cnName = "" Or enName = "" Then GoTo NextRow
        
        ' 检查工作表是否已存在
        If SheetExists(cnName) Then
            wsCatalog.Cells(i, 6).Value = "已存在"
            GoTo NextRow
        End If
        
        ' 获取来源表数量
        sourceCount = Val(wsCatalog.Cells(i, 4).Value)
        If sourceCount < 1 Then sourceCount = 1
        
        ' 创建新工作表
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
        ws.Name = cnName
        
        ' 初始化工作表结构
        InitializeTableSheet ws, enName, cnName, sourceCount
        
        ' 添加按钮（在B2位置）
        Set btn = ws.Buttons.Add(10, 45, 120, 28)
        With btn
            .Caption = "添加来源表"
            .OnAction = "AddSourceTableToCurrent"
            .Font.Size = 11
            .Font.Bold = True
        End With
        
        ' 更新状态
        wsCatalog.Cells(i, 6).Value = "已创建"
        createdCount = createdCount + 1
        
NextRow:
    Next i
    
    Application.ScreenUpdating = True
    
    MsgBox "完成！共创建 " & createdCount & " 个表工作表。" & vbCrLf & _
           "请在各工作表中填写字段映射信息。", vbInformation, "生成完成"
End Sub

' ============================================
' 主功能2：删除所有数据表工作表
' ============================================
Sub DeleteAllTableSheets()
    Dim ws As Worksheet
    Dim count As Long
    
    If MsgBox("确定要删除所有数据表工作表吗？" & vbCrLf & _
              "（目录和说明工作表将保留）", vbQuestion + vbYesNo, "确认删除") = vbNo Then
        Exit Sub
    End If
    
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    
    count = 0
    For Each ws In ThisWorkbook.Worksheets
        If ws.Name <> "目录" And ws.Name <> "说明" Then
            ws.Delete
            count = count + 1
        End If
    Next ws
    
    ' 清空目录状态
    Dim lastRow As Long
    lastRow = ThisWorkbook.Sheets("目录").Cells(ThisWorkbook.Sheets("目录").Rows.Count, "B").End(xlUp).Row
    ThisWorkbook.Sheets("目录").Range("F9:F" & lastRow).ClearContents
    
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    
    MsgBox "已删除 " & count & " 个工作表。", vbInformation, "删除完成"
End Sub

' ============================================
' 主功能3：为当前工作表添加来源表
' ============================================
Sub AddSourceTableToCurrent()
    Dim ws As Worksheet
    Set ws = ActiveSheet
    
    ' 检查是否在目录或说明页
    If ws.Name = "目录" Or ws.Name = "说明" Then
        MsgBox "请在数据表工作表中使用此功能！", vbExclamation
        Exit Sub
    End If
    
    AddSourceTable ws
End Sub

' ============================================
' 核心函数：初始化表工作表结构
' ============================================
Private Sub InitializeTableSheet(ws As Worksheet, enName As String, cnName As String, sourceCount As Long)
    Dim col As Long
    Dim i As Long
    Dim suffix As String
    
    ' 第1行：标题
    ws.MergeCells "A1:K1"
    ws.Cells(1, 1).Value = "目标表：" & enName & "（" & cnName & "）"
    ws.Cells(1, 1).Font.Size = 14
    ws.Cells(1, 1).Font.Bold = True
    
    ' 第2行：说明
    ws.MergeCells "A2:K2"
    ws.Cells(2, 2).Value = "点击右侧按钮添加更多来源表 →"
    ws.Cells(2, 2).Font.Color = RGB(128, 128, 128)
    
    ' 第3行：组标签
    ws.Cells(3, 7).Value = "来源表1：[源系统名称]"
    ws.Cells(3, 7).Font.Bold = True
    ws.Cells(3, 7).Font.Color = RGB(255, 255, 255)
    ws.Cells(3, 7).Interior.Color = COLOR_GREEN
    ws.Cells(3, 7).HorizontalAlignment = xlCenter
    ws.MergeCells "G3:K3"
    
    ' 第4行：列头
    ' 公共列（蓝色）
    Dim publicHeaders As Variant
    publicHeaders = Array("字段英文名", "字段中文名", "值域类型", "值域约束", "是否主键", "启用标记")
    For i = 0 To 5
        col = i + 1
        ws.Cells(4, col).Value = publicHeaders(i)
        SetHeaderStyle ws.Cells(4, col), COLOR_BLUE
    Next i
    
    ' 来源表1列（绿色）
    Dim sourceHeaders As Variant
    sourceHeaders = Array("源系统表英文名称", "字段英文名", "字段中文名", "映射规则", "关联条件")
    For i = 0 To 4
        col = 7 + i
        ws.Cells(4, col).Value = sourceHeaders(i)
        SetHeaderStyle ws.Cells(4, col), COLOR_GREEN
    Next i
    
    ' 添加数据行边框（到第50行）
    Dim row As Long
    For row = 5 To 50
        For col = 1 To 11
            ws.Cells(row, col).Borders.LineStyle = xlContinuous
        Next col
    Next row
    
    ' 设置列宽
    ws.Columns("A:A").ColumnWidth = 12
    ws.Columns("B:B").ColumnWidth = 12
    ws.Columns("C:C").ColumnWidth = 10
    ws.Columns("D:D").ColumnWidth = 10
    ws.Columns("E:E").ColumnWidth = 8
    ws.Columns("F:F").ColumnWidth = 8
    ws.Columns("G:G").ColumnWidth = 22
    ws.Columns("H:H").ColumnWidth = 12
    ws.Columns("I:I").ColumnWidth = 12
    ws.Columns("J:J").ColumnWidth = 12
    ws.Columns("K:K").ColumnWidth = 22
End Sub

' ============================================
' 核心函数：添加来源表
' ============================================
Private Sub AddSourceTable(ws As Worksheet)
    Dim sourceCount As Long
    Dim newCol As Long
    Dim lastCol As Long
    Dim i As Long
    Dim sourceName As String
    Dim suffix As String
    Dim color As Long
    
    ' 检测当前来源表数量
    sourceCount = CountSourceTables(ws)
    
    If sourceCount >= 8 Then
        MsgBox "来源表数量已达上限（最多8个）！", vbExclamation
        Exit Sub
    End If
    
    ' 获取新来源表名称
    sourceName = InputBox("请输入来源表名称：" & vbCrLf & _
                          "示例：来源表2：信贷系统客户表", _
                          "添加新来源表", _
                          "来源表" & (sourceCount + 1) & "：[源系统名称]")
    
    If sourceName = "" Then Exit Sub
    
    ' 找到最后一列
    lastCol = ws.Cells(4, ws.Columns.Count).End(xlToLeft).Column
    
    ' 在最后一列前插入5列（备注列之前）
    If ws.Cells(4, lastCol).Value = "备注" Then
        ws.Columns(lastCol).Insert
        ws.Columns(lastCol).Insert
        ws.Columns(lastCol).Insert
        ws.Columns(lastCol).Insert
        ws.Columns(lastCol).Insert
        newCol = lastCol
    Else
        newCol = lastCol + 1
    End If
    
    ' 获取颜色
    color = GetSourceColor(sourceCount + 1)
    
    ' 添加组标签（第3行）
    ws.Cells(3, newCol).Value = sourceName
    ws.Cells(3, newCol).Resize(1, 5).Merge
    ws.Cells(3, newCol).Font.Bold = True
    ws.Cells(3, newCol).Font.Color = RGB(255, 255, 255)
    ws.Cells(3, newCol).Interior.Color = color
    ws.Cells(3, newCol).HorizontalAlignment = xlCenter
    
    ' 添加列头（第4行）
    Dim headers As Variant
    headers = Array("源系统表英文名称", "字段英文名", "字段中文名", "映射规则", "关联条件")
    
    If sourceCount = 0 Then
        suffix = ""
    Else
        suffix = "." & sourceCount
    End If
    
    For i = 0 To 4
        ws.Cells(4, newCol + i).Value = headers(i) & suffix
        SetHeaderStyle ws.Cells(4, newCol + i), color
    Next i
    
    ' 添加数据行边框（到第50行）
    Dim row As Long
    For row = 5 To 50
        For i = 0 To 4
            ws.Cells(row, newCol + i).Borders.LineStyle = xlContinuous
        Next i
    Next row
    
    ' 设置列宽
    ws.Columns(newCol).ColumnWidth = 22
    ws.Columns(newCol + 1).ColumnWidth = 12
    ws.Columns(newCol + 2).ColumnWidth = 12
    ws.Columns(newCol + 3).ColumnWidth = 12
    ws.Columns(newCol + 4).ColumnWidth = 22
    
    MsgBox "已添加：" & sourceName & vbCrLf & _
           "列位置：" & newCol & " - " & (newCol + 4), vbInformation, "添加成功"
End Sub

' ============================================
' 辅助函数
' ============================================

Private Function SheetExists(sheetName As String) As Boolean
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets(sheetName)
    SheetExists = Not ws Is Nothing
End Function

Private Function CountSourceTables(ws As Worksheet) As Long
    Dim col As Long
    Dim count As Long
    Dim cellVal As String
    
    count = 0
    For col = 7 To ws.Cells(4, ws.Columns.Count).End(xlToLeft).Column
        cellVal = ws.Cells(4, col).Value
        If InStr(cellVal, "源系统表英文名称") > 0 Then
            count = count + 1
        End If
    Next col
    
    CountSourceTables = count
End Function

Private Function GetSourceColor(index As Long) As Long
    Select Case index
        Case 1: GetSourceColor = COLOR_GREEN
        Case 2: GetSourceColor = COLOR_ORANGE
        Case 3: GetSourceColor = 15519518   ' 蓝色
        Case 4: GetSourceColor = COLOR_YELLOW
        Case 5: GetSourceColor = 11119017   ' 灰色
        Case 6: GetSourceColor = 16744703   ' 红色
        Case 7: GetSourceColor = 10498160   ' 紫色
        Case 8: GetSourceColor = 10509148   ' 青色
    End Select
End Function

Private Sub SetHeaderStyle(cell As Range, color As Long)
    With cell
        .Interior.Color = color
        .Font.Bold = True
        .Font.Color = RGB(255, 255, 255)
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Borders.LineStyle = xlContinuous
    End With
End Sub
