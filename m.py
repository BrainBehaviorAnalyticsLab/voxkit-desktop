from voxkit.gui.components import CSVVisualizationWidget

if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = CSVVisualizationWidget('/Users/beckett/.tpe-speech-analysis/datasets/dsvdsv/defaultanalyzer_summary.csv')
    widget.show()
    sys.exit(app.exec())