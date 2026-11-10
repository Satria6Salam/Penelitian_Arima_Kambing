Attribute VB_Name = "Modul_Peramalan_SARIMA"
' ============================================================================
' Modul VBA peramalan rekursif SARIMA(1,0,0)x(1,1,0,12) pada ln(permintaan)
' Dibuat oleh 11_implementasi_access.py. Cara impor di MS Access:
'   Database Tools -> Visual Basic -> File -> Import File... -> pilih file ini.
' Cara pakai: jalankan IsiPeramalan 6 (Immediate Window: IsiPeramalan 6)
' atau panggil dari tombol/form/makro (RunCode: IsiPeramalan(6)).
' Sumber data: Tbl_Volume_Bulanan, parameter: Tbl_Parameter_SARIMA,
' hasil ditulis ke Tbl_Peramalan (satu batch per Tanggal_Dibuat).
' ============================================================================
Option Compare Database
Option Explicit

Private Function Param(ByVal nama As String) As Double
    Param = DLookup("Nilai", "Tbl_Parameter_SARIMA", "Nama_Parameter='" & nama & "'")
End Function

Public Function IsiPeramalan(Optional ByVal horizon As Integer = 6) As Boolean
    Dim db As DAO.Database, rs As DAO.Recordset, rsOut As DAO.Recordset
    Dim n As Long, i As Long, h As Integer, j As Integer
    Dim lnY() As Double, w() As Double
    Dim phi As Double, Phi12 As Double, sigma2 As Double, z As Double
    Dim wHat As Double, lnHat As Double, se As Double, sumPsi As Double
    Dim periodeAkhir As Date, dibuat As Date

    phi = Param("ar.L1"): Phi12 = Param("ar.S.L12")
    sigma2 = Param("sigma2"): z = Param("Z_95")

    Set db = CurrentDb
    Set rs = db.OpenRecordset("SELECT Periode, Permintaan_Kg FROM Tbl_Volume_Bulanan ORDER BY Periode", dbOpenSnapshot)
    rs.MoveLast: n = rs.RecordCount: rs.MoveFirst
    If n < 26 Then
        MsgBox "Data bulanan minimal 26 bulan.", vbExclamation
        Exit Function
    End If

    ReDim lnY(1 To n + horizon): ReDim w(1 To n + horizon)
    For i = 1 To n
        lnY(i) = Log(rs!Permintaan_Kg)
        periodeAkhir = rs!Periode
        rs.MoveNext
    Next i
    rs.Close
    For i = 13 To n
        w(i) = lnY(i) - lnY(i - 12)
    Next i

    dibuat = Now()
    Set rsOut = db.OpenRecordset("Tbl_Peramalan", dbOpenDynaset)
    For h = 1 To horizon
        i = n + h
        wHat = phi * w(i - 1) + Phi12 * w(i - 12) - phi * Phi12 * w(i - 13)
        lnHat = lnY(i - 12) + wHat
        lnY(i) = lnHat: w(i) = wHat
        sumPsi = 0
        For j = 0 To h - 1
            sumPsi = sumPsi + phi ^ (2 * j)
        Next j
        se = Sqr(sigma2 * sumPsi)
        rsOut.AddNew
        rsOut!Nama_Model = "SARIMA(1,0,0)x(1,1,0,12) log"
        rsOut!Periode = DateAdd("m", h, periodeAkhir)
        rsOut!Horizon = h
        rsOut!Prediksi_Kg = Exp(lnHat)
        rsOut!Batas_Bawah_95_Kg = Exp(lnHat - z * se)
        rsOut!Batas_Atas_95_Kg = Exp(lnHat + z * se)
        rsOut!Sumber = "VBA Modul_Peramalan_SARIMA"
        rsOut!Tanggal_Dibuat = dibuat
        rsOut.Update
    Next h
    rsOut.Close
    IsiPeramalan = True
    MsgBox "Peramalan " & horizon & " bulan tersimpan di Tbl_Peramalan. Buka qry_11_Peramalan_6_Bulan.", vbInformation
End Function
