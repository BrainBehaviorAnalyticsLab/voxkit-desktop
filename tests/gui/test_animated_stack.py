from PyQt6.QtWidgets import QLabel

from voxkit.gui.components.animate_stack import AnimatedStackedWidget


class TestAnimatedStackedWidget:
    def test_initial_index_is_zero(self, qtbot):
        stack = AnimatedStackedWidget()
        qtbot.addWidget(stack)
        stack.addWidget(QLabel("Page 0"))
        stack.addWidget(QLabel("Page 1"))

        assert stack.currentIndex() == 0

    def test_slide_to_valid_index(self, qtbot):
        stack = AnimatedStackedWidget()
        qtbot.addWidget(stack)
        stack.addWidget(QLabel("Page 0"))
        stack.addWidget(QLabel("Page 1"))
        stack.resize(400, 300)
        stack.show()

        stack.slideToIndex(1)

        # After animation finishes, current index should be 1
        qtbot.waitUntil(lambda: stack.currentIndex() == 1, timeout=1000)

    def test_slide_to_same_index_is_noop(self, qtbot):
        stack = AnimatedStackedWidget()
        qtbot.addWidget(stack)
        stack.addWidget(QLabel("Page 0"))
        stack.addWidget(QLabel("Page 1"))

        stack.slideToIndex(0)
        assert stack.currentIndex() == 0

    def test_slide_to_negative_index_is_noop(self, qtbot):
        stack = AnimatedStackedWidget()
        qtbot.addWidget(stack)
        stack.addWidget(QLabel("Page 0"))

        stack.slideToIndex(-1)
        assert stack.currentIndex() == 0

    def test_slide_to_out_of_bounds_is_noop(self, qtbot):
        stack = AnimatedStackedWidget()
        qtbot.addWidget(stack)
        stack.addWidget(QLabel("Page 0"))

        stack.slideToIndex(5)
        assert stack.currentIndex() == 0

    def test_add_multiple_widgets(self, qtbot):
        stack = AnimatedStackedWidget()
        qtbot.addWidget(stack)

        for i in range(5):
            stack.addWidget(QLabel(f"Page {i}"))

        assert stack.count() == 5
